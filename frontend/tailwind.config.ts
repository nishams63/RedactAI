import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./features/**/*.{ts,tsx}",
    "./providers/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#eef3ff",
          100: "#dde7ff",
          200: "#c2d3ff",
          300: "#9db6ff",
          400: "#7899ff",
          500: "#4F7CFF",
          600: "#3a5fdb",
          700: "#2c48b0",
          800: "#203489",
          900: "#152266",
          950: "#0c1440",
        },
        surface: {
          50: "#f4f6f9",
          100: "#e8ebf0",
          200: "#d1d7e1",
          300: "#b0b9ca",
          400: "#8a96ac",
          500: "#AEB6C4",
          600: "#6b7a92",
          700: "#3d4b63",
          800: "#181F2E",
          900: "#121826",
          950: "#090B12",
        },
        accent: {
          teal: "#00E1C7",
          lime: "#D7FF7E",
          danger: "#FF5C7A",
          warning: "#FFC857",
          success: "#41E98A",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "-apple-system", "sans-serif"],
        display: ["Outfit", "Inter", "system-ui", "sans-serif"],
      },
      borderRadius: {
        "2xl": "16px",
        "3xl": "20px",
        "4xl": "24px",
      },
      animation: {
        "fade-in": "fadeIn 0.4s cubic-bezier(0.22, 1, 0.36, 1)",
        "slide-up": "slideUp 0.4s cubic-bezier(0.22, 1, 0.36, 1)",
        "slide-in-right": "slideInRight 0.35s cubic-bezier(0.22, 1, 0.36, 1)",
        "pulse-soft": "pulseSoft 3s ease-in-out infinite",
        "float": "float 6s ease-in-out infinite",
        "glow": "glow 4s ease-in-out infinite alternate",
        "shimmer": "shimmer 2s linear infinite",
        "scan": "scan 3s ease-in-out infinite",
      },
      keyframes: {
        fadeIn: {
          "0%": { opacity: "0", transform: "scale(0.98)" },
          "100%": { opacity: "1", transform: "scale(1)" },
        },
        slideUp: {
          "0%": { opacity: "0", transform: "translateY(16px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        slideInRight: {
          "0%": { opacity: "0", transform: "translateX(24px)" },
          "100%": { opacity: "1", transform: "translateX(0)" },
        },
        pulseSoft: {
          "0%, 100%": { opacity: "0.4" },
          "50%": { opacity: "0.8" },
        },
        float: {
          "0%, 100%": { transform: "translateY(0)" },
          "50%": { transform: "translateY(-12px)" },
        },
        glow: {
          "0%": { opacity: "0.4", filter: "blur(40px)" },
          "100%": { opacity: "0.8", filter: "blur(60px)" },
        },
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
        scan: {
          "0%, 100%": { transform: "translateY(-100%)", opacity: "0" },
          "50%": { transform: "translateY(100%)", opacity: "1" },
        },
      },
    },
  },
  plugins: [],
};

export default config;
