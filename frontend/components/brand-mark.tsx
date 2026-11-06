import { cn } from "@/lib/cn";

export function BrandMark({
  className,
  variant = "color",
}: {
  readonly className?: string;
  readonly variant?: "color" | "inverse";
}) {
  const gradientId = variant === "color" ? "hps-leaf" : "hps-leaf-inverse";
  return (
    <svg
      viewBox="0 0 64 64"
      className={cn("shrink-0", className)}
      role="img"
      aria-label="HealthPolicy Simulator"
    >
      <defs>
        <linearGradient id={gradientId} x1="0" y1="0" x2="0.85" y2="1">
          <stop offset="0%" stopColor={variant === "color" ? "#3cae7d" : "#ffffff"} />
          <stop offset="100%" stopColor={variant === "color" ? "#007a4f" : "#f2f5f5"} />
        </linearGradient>
      </defs>
      <path
        d="M32 2.5C18.6 14.4 6 26.6 6 40.2a26 26 0 0 0 52 0C58 26.6 45.4 14.4 32 2.5Z"
        fill={`url(#${gradientId})`}
      />
      <path
        d="M32 8v49"
        stroke={variant === "color" ? "#ffffff" : "#74767b"}
        strokeOpacity={variant === "color" ? 0.32 : 0.18}
        strokeWidth="1.4"
      />
      <text
        x="32"
        y="44"
        textAnchor="middle"
        fontFamily="var(--font-roboto-condensed), Arial Narrow, Arial, sans-serif"
        fontSize="20"
        fontWeight="700"
        letterSpacing="0.5"
        fill={variant === "color" ? "#ffffff" : "#74767b"}
      >
        HP
      </text>
    </svg>
  );
}
