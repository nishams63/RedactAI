"""RedactAI Performance Profiler, Load Tester, and Regression Detector."""
import os
import csv
import json
import time
import psutil
import statistics
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy.orm import Session
# reportlab imports deferred to lazy PDF generation handler to prevent startup dependency side-effects

from models.ai_models import PerformanceBenchmark, PerformanceProfile, BenchmarkQuestion
from services.legal_ai.cache_manager import CacheManager
from services.legal_ai.retriever import LegalRetriever
from services.legal_ai.slm import LocalSLMInferenceEngine

REPORTS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "local_storage",
    "reports"
)
os.makedirs(REPORTS_DIR, exist_ok=True)

class PerformanceProfiler:
    def __init__(self, db: Session):
        self.db = db
        self.cache_manager = CacheManager()

    def run_load_test(self, concurrency: int = 10) -> PerformanceBenchmark:
        """Simulates parallel execution of RAG pipeline across multiple threads to load test the system."""
        # 1. Fetch search questions
        questions = self.db.query(BenchmarkQuestion).limit(50).all()
        queries = [q.question for q in questions] if questions else [
            "What are the consequences of disclosing Confidential Information?",
            "How is the term of confidentiality defined in the NDA?",
            "What exceptions exist for confidentiality compliance requirements?",
            "What governing law rules apply in the contract under dispute?",
            "Is there a mutual limitation of liability clause present in this draft?"
        ]

        # Cycle queries to match concurrency if needed
        while len(queries) < concurrency:
            queries.extend(queries)
        test_queries = queries[:concurrency]

        # Init engines
        retriever = LegalRetriever()
        slm = LocalSLMInferenceEngine()

        latencies = []
        failures = 0
        start_cpu = psutil.cpu_percent(interval=None)
        start_ram = psutil.virtual_memory().percent

        def execute_query_flow(q_str: str) -> float:
            flow_start = time.time()
            try:
                # Run retrieval
                results = retriever.retrieve(q_str, top_k=5)
                # Run reasoning
                context = "\n".join([r[0]["text"] for r in results])
                slm.generate_response(
                    system_prompt="You are a legal assistant. Answer with citations.",
                    user_prompt=f"Context:\n{context}\n\nQuestion: {q_str}"
                )
                return (time.time() - flow_start) * 1000.0
            except Exception as e:
                nonlocal failures
                failures += 1
                return 0.0

        # Run concurrent executions
        start_time = time.time()
        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = [executor.submit(execute_query_flow, q) for q in test_queries]
            for f in futures:
                lat = f.result()
                if lat > 0.0:
                    latencies.append(lat)

        total_duration = time.time() - start_time
        end_cpu = psutil.cpu_percent(interval=None)
        end_ram = psutil.virtual_memory().percent

        avg_latency = statistics.mean(latencies) if latencies else 0.0
        peak_latency = max(latencies) if latencies else 0.0
        throughput = concurrency / total_duration if total_duration > 0 else 0.0
        failure_rate = failures / concurrency

        # Fetch cache hit/miss stats
        cache_stats = self.cache_manager.get_stats()

        # Build current benchmark dict
        current_metrics = {
            "concurrency": concurrency,
            "throughput": round(throughput, 2),
            "avg_latency": round(avg_latency, 2),
            "peak_latency": round(peak_latency, 2),
            "failure_rate": round(failure_rate, 4),
            "cpu_util": round((start_cpu + end_cpu) / 2.0, 1),
            "ram_util": round((start_ram + end_ram) / 2.0, 1),
            "cache_stats": cache_stats
        }

        # Perform regression detection
        imp_report, reg_report, regression_status = self.detect_regression(current_metrics)

        # Write benchmark run record to database
        benchmark = PerformanceBenchmark(
            concurrency=concurrency,
            throughput=round(throughput, 2),
            avg_latency=round(avg_latency, 2),
            peak_latency=round(peak_latency, 2),
            failure_rate=round(failure_rate, 4),
            cpu_util=round((start_cpu + end_cpu) / 2.0, 1),
            ram_util=round((start_ram + end_ram) / 2.0, 1),
            cache_stats=cache_stats,
            improvement_report=imp_report,
            regression_report=reg_report
        )
        self.db.add(benchmark)
        self.db.commit()

        # Auto export file formats
        self.export_reports(benchmark)

        return benchmark

    def detect_regression(self, current: dict) -> tuple:
        """Compares current load test against the latest historical benchmark to flag improvements or regressions."""
        past = self.db.query(PerformanceBenchmark).order_by(PerformanceBenchmark.created_at.desc()).first()
        if not past:
            return {}, {}, "UNCHANGED"

        improvements = {}
        regressions = {}
        status = "UNCHANGED"

        # Compare Latency (lower is better, threshold 10% change)
        lat_diff = (current["avg_latency"] - past.avg_latency) / past.avg_latency
        if lat_diff > 0.10:
            regressions["avg_latency"] = {
                "message": f"Average latency increased by {round(lat_diff * 100, 1)}% from {past.avg_latency}ms to {current['avg_latency']}ms.",
                "severity": "CRITICAL"
            }
        elif lat_diff < -0.10:
            improvements["avg_latency"] = {
                "message": f"Average latency improved by {round(abs(lat_diff) * 100, 1)}% from {past.avg_latency}ms to {current['avg_latency']}ms."
            }

        # Compare Throughput (higher is better, threshold 10% change)
        thru_diff = (current["throughput"] - past.throughput) / past.throughput
        if thru_diff < -0.10:
            regressions["throughput"] = {
                "message": f"Throughput decreased by {round(abs(thru_diff) * 100, 1)}% from {past.throughput} req/s to {current['throughput']} req/s.",
                "severity": "CRITICAL"
            }
        elif thru_diff > 0.10:
            improvements["throughput"] = {
                "message": f"Throughput increased by {round(thru_diff * 100, 1)}% from {past.throughput} req/s to {current['throughput']} req/s."
            }

        # Compare Failure Rate (lower is better, threshold 5% change)
        fail_diff = current["failure_rate"] - past.failure_rate
        if fail_diff > 0.05:
            regressions["failure_rate"] = {
                "message": f"Failure rate increased by {round(fail_diff * 100, 1)}% from {round(past.failure_rate*100, 1)}% to {round(current['failure_rate']*100, 1)}%.",
                "severity": "CRITICAL"
            }

        if regressions:
            status = "REGRESSED"
        elif improvements:
            status = "IMPROVED"

        return improvements, regressions, status

    def export_reports(self, record: PerformanceBenchmark):
        """Generates performance report exports in JSON, CSV, and PDF formats."""
        # 1. JSON Report
        json_path = os.path.join(REPORTS_DIR, "Performance_Report.json")
        report_data = {
            "run_id": str(record.id),
            "created_at": record.created_at.isoformat() if record.created_at else datetime.now().isoformat(),
            "concurrency": record.concurrency,
            "throughput_req_sec": record.throughput,
            "average_latency_ms": record.avg_latency,
            "peak_latency_ms": record.peak_latency,
            "failure_rate": record.failure_rate,
            "cpu_utilization": record.cpu_util,
            "ram_utilization": record.ram_util,
            "cache_statistics": record.cache_stats,
            "improvement_report": record.improvement_report,
            "regression_report": record.regression_report
        }
        with open(json_path, "w") as f:
            json.dump(report_data, f, indent=4)

        # 2. CSV Report (Historical overview append/rewrite)
        csv_path = os.path.join(REPORTS_DIR, "Performance_Report.csv")
        history = self.db.query(PerformanceBenchmark).order_by(PerformanceBenchmark.created_at.asc()).all()
        with open(csv_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Benchmark Run ID", "Timestamp", "Concurrency", 
                "Throughput (req/s)", "Avg Latency (ms)", "Peak Latency (ms)", 
                "Failure Rate", "CPU (%)", "RAM (%)"
            ])
            for h in history:
                writer.writerow([
                    str(h.id), h.created_at.isoformat() if h.created_at else datetime.now().isoformat(),
                    h.concurrency, h.throughput, h.avg_latency, h.peak_latency,
                    h.failure_rate, h.cpu_util, h.ram_util
                ])

        # 3. PDF Report using ReportLab
        pdf_path = os.path.join(REPORTS_DIR, "Performance_Report.pdf")
        
        # Remove any existing error file first
        err_txt_path = pdf_path.replace(".pdf", "_error.txt")
        if os.path.exists(err_txt_path):
            try:
                os.remove(err_txt_path)
            except Exception:
                pass

        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.lib import colors
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

            doc = SimpleDocTemplate(pdf_path, pagesize=letter, leftMargin=40, rightMargin=40, topMargin=40, bottomMargin=40)
            styles = getSampleStyleSheet()
            story = []

            # Color palette
            primary_color = colors.HexColor("#0f172a") # dark slate
            secondary_color = colors.HexColor("#3b82f6") # blue
            text_color = colors.HexColor("#334155")
            light_bg = colors.HexColor("#f8fafc")

            title_style = ParagraphStyle(
                "DocTitle",
                parent=styles["Normal"],
                fontName="Helvetica-Bold",
                fontSize=24,
                leading=28,
                textColor=primary_color,
                spaceAfter=6
            )
            subtitle_style = ParagraphStyle(
                "DocSubtitle",
                parent=styles["Normal"],
                fontName="Helvetica",
                fontSize=12,
                leading=16,
                textColor=secondary_color,
                spaceAfter=20
            )
            h1_style = ParagraphStyle(
                "SectionHeader",
                parent=styles["Normal"],
                fontName="Helvetica-Bold",
                fontSize=16,
                leading=20,
                textColor=primary_color,
                spaceBefore=14,
                spaceAfter=10
            )
            body_style = ParagraphStyle(
                "BodyTextCustom",
                parent=styles["Normal"],
                fontName="Helvetica",
                fontSize=10,
                leading=14,
                textColor=text_color,
                spaceAfter=10
            )

            story.append(Paragraph("RedactAI Performance Benchmark Report", title_style))
            story.append(Paragraph(f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (IST) | Run ID: {record.id}", subtitle_style))
            story.append(Spacer(1, 10))

            # Main metrics table
            story.append(Paragraph("System Load & Processing Performance", h1_style))
            metrics_data = [
                [Paragraph("<b>Metric</b>", body_style), Paragraph("<b>Value</b>", body_style), Paragraph("<b>Target Threshold</b>", body_style)],
                [Paragraph("Concurrency Load", body_style), Paragraph(f"{record.concurrency} threads", body_style), Paragraph("-", body_style)],
                [Paragraph("Throughput", body_style), Paragraph(f"{record.throughput} reqs/sec", body_style), Paragraph("&gt; 5.0 reqs/sec", body_style)],
                [Paragraph("Average Query Latency", body_style), Paragraph(f"{record.avg_latency} ms", body_style), Paragraph("&lt; 2000 ms", body_style)],
                [Paragraph("Peak Query Latency", body_style), Paragraph(f"{record.peak_latency} ms", body_style), Paragraph("&lt; 5000 ms", body_style)],
                [Paragraph("Request Failure Rate", body_style), Paragraph(f"{record.failure_rate} %", body_style), Paragraph("0.0 %", body_style)],
                [Paragraph("Average CPU Load", body_style), Paragraph(f"{record.cpu_util} %", body_style), Paragraph("&lt; 85 %", body_style)],
                [Paragraph("Average Memory Load", body_style), Paragraph(f"{record.ram_util} %", body_style), Paragraph("&lt; 90 %", body_style)]
            ]
            t_metrics = Table(metrics_data, colWidths=[200, 160, 170])
            t_metrics.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), light_bg),
                ('BOTTOMPADDING', (0,0), (-1,0), 6),
                ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
                ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, light_bg])
            ]))
            story.append(t_metrics)
            story.append(Spacer(1, 15))

            # Cache Statistics Table
            story.append(Paragraph("Subsystem Cache Hit/Miss Audits", h1_style))
            cache_data = [
                [Paragraph("<b>Cache Scope</b>", body_style), Paragraph("<b>Item Count</b>", body_style), Paragraph("<b>Hits</b>", body_style), Paragraph("<b>Misses</b>", body_style), Paragraph("<b>Hit Rate</b>", body_style)]
            ]
            for key, stats in record.cache_stats.items():
                cache_data.append([
                    Paragraph(key.upper(), body_style),
                    Paragraph(str(stats.get("item_count", 0)), body_style),
                    Paragraph(str(stats.get("hits", 0)), body_style),
                    Paragraph(str(stats.get("misses", 0)), body_style),
                    Paragraph(f"{round(stats.get('hit_rate', 0.0) * 100, 1)} %", body_style)
                ])
            t_cache = Table(cache_data, colWidths=[130, 100, 100, 100, 100])
            t_cache.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), light_bg),
                ('BOTTOMPADDING', (0,0), (-1,0), 6),
                ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
                ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, light_bg])
            ]))
            story.append(t_cache)
            story.append(Spacer(1, 15))

            # Regression / Improvement section
            story.append(Paragraph("Performance Regression Analysis", h1_style))
            if not record.regression_report and not record.improvement_report:
                story.append(Paragraph("No historical baseline found. Performance comparisons will activate on subsequent test runs.", body_style))
            else:
                if record.improvement_report:
                    story.append(Paragraph("<b>Improvements Detected:</b>", body_style))
                    for metric, detail in record.improvement_report.items():
                        story.append(Paragraph(f"• <font color='green'>[IMPROVEMENT]</font> {detail.get('message')}", body_style))
                    story.append(Spacer(1, 5))
                if record.regression_report:
                    story.append(Paragraph("<b>Regressions Detected:</b>", body_style))
                    for metric, detail in record.regression_report.items():
                        story.append(Paragraph(f"• <font color='red'>[REGRESSION - {detail.get('severity')}]</font> {detail.get('message')}", body_style))
                else:
                    story.append(Paragraph("<font color='green'>✓ No performance regressions detected compared to previous baseline.</font>", body_style))

            doc.build(story)
            print(f"Successfully generated reports: JSON, CSV, PDF saved in {REPORTS_DIR}")
        except (ImportError, ModuleNotFoundError) as e:
            import logging
            logging.getLogger("redactai.performance_profiler").warning(
                f"ReportLab is not installed. Skipping performance PDF generation: {e}"
            )
            try:
                with open(err_txt_path, "w") as f:
                    f.write("Performance PDF report is unavailable because reportlab package is missing.")
            except Exception:
                pass
