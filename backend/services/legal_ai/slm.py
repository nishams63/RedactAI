import time
from typing import Dict, Any
from services.legal_ai.cache_manager import CacheManager

class LocalSLMInferenceEngine:
    def __init__(self, model_name: str = "Qwen/Qwen2.5-0.5B-Instruct"):
        self.model_name = model_name
        self.cache_manager = CacheManager()
        self._load_slm()
        self.warm_up()

    def _load_slm(self):
        """Load local SLM model if transformers/torch resources are available."""
        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModelForCausalLM.from_pretrained(self.model_name)
            self.use_fallback = False
        except Exception as e:
            print(f"SLM local loader fallback initiated: {e}")
            self.use_fallback = True

    def warm_up(self):
        """Pre-heats the SLM or fallback tokenizer context to ensure first-run query times are fast."""
        if self.use_fallback:
            self._rule_based_fallback_generation("Warm up", "Test input")
        else:
            try:
                import torch
                inputs = self.tokenizer("Warm up test", return_tensors="pt")
                with torch.no_grad():
                    self.model.generate(**inputs, max_new_tokens=5, pad_token_id=self.tokenizer.eos_token_id)
            except Exception as e:
                print(f"Warm up execution skipped: {e}")

    def generate_response(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        """Generate response with explicit indication of the reasoning engine used, checking response cache."""
        cache_key = f"{system_prompt}_{user_prompt}"
        cached = self.cache_manager.get("slm_response", cache_key)
        if cached:
            return cached

        start_time = time.time()
        
        if self.use_fallback:
            answer = self._rule_based_fallback_generation(system_prompt, user_prompt)
            engine_name = "Rule-Based Fallback Engine"
        else:
            try:
                import torch
                full_prompt = f"<|im_start|>system\n{system_prompt}<|im_end|>\n<|im_start|>user\n{user_prompt}<|im_end|>\n<|im_start|>assistant\n"
                
                inputs = self.tokenizer(full_prompt, return_tensors="pt")
                with torch.no_grad():
                    outputs = self.model.generate(
                        **inputs,
                        max_new_tokens=250,
                        temperature=0.2,
                        do_sample=True,
                        pad_token_id=self.tokenizer.eos_token_id
                    )
                
                generated_ids = [
                    output_ids[len(input_ids):] for input_ids, output_ids in zip(inputs.input_ids, outputs)
                ]
                answer = self.tokenizer.decode(generated_ids[0], skip_special_tokens=True).strip()
                engine_name = f"Small Language Model ({self.model_name})"
            except Exception as e:
                print(f"SLM inference exception, running fallback: {e}")
                answer = self._rule_based_fallback_generation(system_prompt, user_prompt)
                engine_name = "Rule-Based Fallback Engine"

        duration_ms = (time.time() - start_time) * 1000.0
        result = {
            "text": answer,
            "reasoning_engine": engine_name,
            "inference_time_ms": round(duration_ms, 2)
        }
        self.cache_manager.set("slm_response", cache_key, result)
        return result

    def _rule_based_fallback_generation(self, system_prompt: str, user_prompt: str) -> str:
        """Determined, context-aware rule-based output generator for legal analysis."""
        # Simple RAG parsing to build summary
        # If retrieved sections are in the prompt, let's extract them
        import re
        
        # Extract context sections
        contexts = []
        context_match = re.search(r"Retrieved Legal Sections:\n(.*?)\n\nQuestion:", system_prompt, re.DOTALL)
        if not context_match:
            context_match = re.search(r"Retrieved Legal Regulations:\n(.*?)\n\nGenerate:", system_prompt, re.DOTALL)
        
        if context_match:
            lines = context_match.group(1).split("\n")
            current_section = ""
            for line in lines:
                if line.startswith("[") or line.strip() == "":
                    if current_section:
                        contexts.append(current_section.strip())
                        current_section = ""
                    if line.strip():
                        current_section += line + "\n"
                else:
                    current_section += line + "\n"
            if current_section:
                contexts.append(current_section.strip())

        # If question is about confidentiality / compliance / etc.
        q = user_prompt.lower()
        if "comply" in q or "compliance" in q:
            # Check context regulations matching
            has_dpdp = any("dpdp" in c.lower() for c in contexts)
            has_rbi = any("rbi" in c.lower() for c in contexts)
            has_uidai = any("uidai" in c.lower() for c in contexts)
            
            violations = []
            score = 100
            if "aadhaar" in q or "aadhaar" in system_prompt.lower():
                if not any("mask" in c.lower() for c in contexts):
                    violations.append("Lack of explicit Aadhaar masking verification process.")
                    score -= 20
            if "consent" in q or "notice" in q:
                violations.append("Absence of explicit DPDP consent notice prior to processing customer PII.")
                score -= 15

            output = f"Compliance Assessment Result:\n- Overall Score: {score}/100\n- Status: {'COMPLIANT' if score >= 80 else 'NON-COMPLIANT'}\n"
            if violations:
                output += "- Violations Detected:\n" + "\n".join([f"  * {v}" for v in violations])
            else:
                output += "- No critical violations detected based on the retrieved compliance policies.\n"
            
            if contexts:
                output += f"\nCitations:\n- {contexts[0].split(']')[0][1:] if ']' in contexts[0] else 'Retrieved Regulation'}"
            return output

        if "why" in q or "explain" in q:
            entity_type = "PII Entity"
            if "aadhaar" in q:
                entity_type = "Aadhaar Number"
                applicable = "UIDAI Guidelines Section 3.2 & DPDP Act 2023"
                rec = "Mask the first 8 digits of the Aadhaar number."
            elif "pan" in q:
                entity_type = "PAN Card"
                applicable = "RBI KYC Guidelines & DPDP Act 2023"
                rec = "Redact or encrypt PAN records before external transmission."
            else:
                applicable = "DPDP Act Section 4"
                rec = "Restrict access and redact before sharing."

            cit_str = contexts[0].split(']')[0][1:] if (contexts and ']' in contexts[0]) else 'General Privacy Guideline'
            return (
                f"Privacy Risk Analysis:\n"
                f"- Entity Detected: {entity_type}\n"
                f"- Classification Reason: Sensitive personal identifier with potential identity theft risks.\n"
                f"- Applicable Law: {applicable}\n"
                f"- Recommendation: {rec}\n"
                f"- Citations: {cit_str}"
            )

        # Standard context summary QA
        if contexts:
            summary_lines = []
            for c in contexts:
                text_part = c.split(']')[1].strip() if ']' in c else c
                summary_lines.append(f"* {text_part}")
            summary = "\n".join(summary_lines)
            
            cit_str_qa = contexts[0].split(']')[0][1:] if ']' in contexts[0] else 'Regulatory Database'
            return (
                f"Based on the retrieved legal sections, here is the context-backed answer:\n"
                f"{summary}\n\n"
                f"Citation: {cit_str_qa}"
            )
            
        return "I cannot find the answer in the retrieved legal sections because no context regulations were supplied."
