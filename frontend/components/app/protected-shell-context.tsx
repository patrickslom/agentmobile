"use client";

import { createContext, useContext } from "react";

type ProtectedShellContextValue = {
  sidebarCollapsed: boolean;
};

const ProtectedShellContext = createContext<ProtectedShellContextValue>({
  sidebarCollapsed: false,
});

export function ProtectedShellContextProvider({
  value,
  children,
}: Readonly<{
  value: ProtectedShellContextValue;
  children: React.ReactNode;
}>) {
  return (
    <ProtectedShellContext.Provider value={value}>
      {children}
    </ProtectedShellContext.Provider>
  );
}

export function useProtectedShell() {
  return useContext(ProtectedShellContext);
}
