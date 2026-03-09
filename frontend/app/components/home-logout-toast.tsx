"use client";

import { useEffect, useMemo, useState } from "react";
import ToastStack, { type ToastItem } from "@/components/ui/toast-stack";

type HomeLogoutToastProps = {
  show: boolean;
};

export default function HomeLogoutToast({ show }: HomeLogoutToastProps) {
  const [visible, setVisible] = useState(show);

  useEffect(() => {
    setVisible(show);
  }, [show]);

  useEffect(() => {
    if (!visible) {
      return;
    }

    const timer = window.setTimeout(() => {
      setVisible(false);
    }, 5000);

    return () => window.clearTimeout(timer);
  }, [visible]);

  const toasts = useMemo<ToastItem[]>(
    () =>
      visible
        ? [
            {
              id: "logged-out",
              title: "Logged out",
              description: "You have been signed out.",
              tone: "info",
            },
          ]
        : [],
    [visible],
  );

  if (toasts.length === 0) {
    return null;
  }

  return <ToastStack toasts={toasts} onDismiss={() => setVisible(false)} />;
}
