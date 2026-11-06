"use client";

import { useState } from "react";

import { Icon } from "@/components/icons";
import { useSettings, useToast } from "@/components/providers";
import { Button } from "@/components/ui/button";

export function CopyButton({
  value,
  label,
  size = "sm",
}: {
  readonly value: string;
  readonly label?: string;
  readonly size?: "sm" | "md";
}) {
  const { t } = useSettings();
  const { push } = useToast();
  const [copied, setCopied] = useState(false);

  const copy = async (): Promise<void> => {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      push(t("common.copied"), "ok");
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      push(t("common.error"), "danger");
    }
  };

  return (
    <Button
      size={size}
      onClick={() => {
        void copy();
      }}
      icon={<Icon name={copied ? "check" : "copy"} size={15} />}
    >
      {label ?? (copied ? t("common.copied") : t("common.copy"))}
    </Button>
  );
}
