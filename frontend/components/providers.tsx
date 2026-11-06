"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { ApiError } from "@/lib/http";
import { translate, type Locale, type MessageKey } from "@/lib/i18n";
import {
  DEFAULT_SETTINGS,
  loadSettings,
  saveSettings,
  type Settings,
} from "@/lib/settings";

interface SettingsContextValue {
  readonly settings: Settings;
  readonly hydrated: boolean;
  readonly locale: Locale;
  readonly t: (key: MessageKey, params?: Readonly<Record<string, string | number>>) => string;
  readonly setSettings: (next: Settings) => void;
  readonly updateSettings: (patch: Partial<Omit<Settings, "version">>) => void;
}

const SettingsContext = createContext<SettingsContextValue | null>(null);

export type ToastTone = "ok" | "warn" | "danger" | "info";

interface Toast {
  readonly id: number;
  readonly message: string;
  readonly tone: ToastTone;
}

interface ToastContextValue {
  readonly push: (message: string, tone?: ToastTone) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

function applyDocumentSettings(settings: Settings): void {
  if (typeof document === "undefined") return;
  const root = document.documentElement;
  root.dataset.theme = settings.theme;
  root.dataset.density = settings.density;
  root.dataset.motion = settings.motion;
  root.lang = settings.locale === "en" ? "en" : "de-AT";
}

function SettingsProvider({ children }: { readonly children: ReactNode }) {
  const [settings, setSettingsState] = useState<Settings>(DEFAULT_SETTINGS);
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    const stored = loadSettings();
    setSettingsState(stored);
    applyDocumentSettings(stored);
    setHydrated(true);
    const onSettings = (event: Event): void => {
      const detail = (event as CustomEvent<Settings>).detail;
      if (detail !== undefined) {
        setSettingsState(detail);
        applyDocumentSettings(detail);
      }
    };
    const onStorage = (event: StorageEvent): void => {
      if (event.key === "hps.settings.v1") {
        const storedNow = loadSettings();
        setSettingsState(storedNow);
        applyDocumentSettings(storedNow);
      }
    };
    window.addEventListener("hps:settings", onSettings);
    window.addEventListener("storage", onStorage);
    return () => {
      window.removeEventListener("hps:settings", onSettings);
      window.removeEventListener("storage", onStorage);
    };
  }, []);

  const setSettings = useCallback((next: Settings) => {
    setSettingsState(next);
    saveSettings(next);
    applyDocumentSettings(next);
  }, []);

  const updateSettings = useCallback(
    (patch: Partial<Omit<Settings, "version">>) => {
      setSettingsState((current) => {
        const next: Settings = { ...current, ...patch, version: 1 };
        saveSettings(next);
        applyDocumentSettings(next);
        return next;
      });
    },
    [],
  );

  const t = useCallback(
    (key: MessageKey, params?: Readonly<Record<string, string | number>>) =>
      translate(settings.locale, key, params),
    [settings.locale],
  );

  const value = useMemo<SettingsContextValue>(
    () => ({
      settings,
      hydrated,
      locale: settings.locale,
      t,
      setSettings,
      updateSettings,
    }),
    [settings, hydrated, t, setSettings, updateSettings],
  );

  return <SettingsContext.Provider value={value}>{children}</SettingsContext.Provider>;
}

function ToastProvider({ children }: { readonly children: ReactNode }) {
  const [toasts, setToasts] = useState<readonly Toast[]>([]);
  const push = useCallback((message: string, tone: ToastTone = "info") => {
    const id = Date.now() + Math.random();
    setToasts((current) => [...current, { id, message, tone }]);
    window.setTimeout(() => {
      setToasts((current) => current.filter((toast) => toast.id !== id));
    }, 4000);
  }, []);
  const value = useMemo<ToastContextValue>(() => ({ push }), [push]);
  return (
    <ToastContext.Provider value={value}>
      {children}
      <div
        aria-live="polite"
        aria-atomic="false"
        className="pointer-events-none fixed bottom-4 right-4 z-50 flex w-80 flex-col gap-2"
      >
        {toasts.map((toast) => (
          <div
            key={toast.id}
            role="status"
            className="pointer-events-auto rounded-md border border-line bg-surface px-3 py-2 text-sm shadow-2"
          >
            <span
              className={
                toast.tone === "ok"
                  ? "text-ok"
                  : toast.tone === "warn"
                    ? "text-warn"
                    : toast.tone === "danger"
                      ? "text-danger"
                      : "text-info"
              }
            >
              {toast.message}
            </span>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

function makeQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 5_000,
        refetchOnWindowFocus: false,
        retry: (failureCount, error) => {
          if (error instanceof ApiError && error.status >= 400 && error.status < 500) return false;
          return failureCount < 2;
        },
        retryDelay: (attempt) => (attempt === 0 ? 300 : 900),
      },
      mutations: {
        retry: false,
      },
    },
  });
}

export function Providers({ children }: { readonly children: ReactNode }) {
  const [client] = useState(makeQueryClient);
  return (
    <QueryClientProvider client={client}>
      <SettingsProvider>
        <ToastProvider>{children}</ToastProvider>
      </SettingsProvider>
    </QueryClientProvider>
  );
}

export function useSettings(): SettingsContextValue {
  const value = useContext(SettingsContext);
  if (value === null) throw new Error("useSettings must be used inside Providers");
  return value;
}

export function useToast(): ToastContextValue {
  const value = useContext(ToastContext);
  if (value === null) throw new Error("useToast must be used inside Providers");
  return value;
}
