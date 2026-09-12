"use client";

import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";

/** 画面共通の枠（③ モックの app-header + page）。文言は t() 経由。 */
export function AppShell({ children }: { children: ReactNode }) {
  const { t } = useTranslation();
  return (
    <>
      <header className="app-header">
        <div className="inner">
          <span className="brand">{t("shell.brand")}</span>
          <span className="user">{t("shell.user")}</span>
        </div>
      </header>
      <main className="page">{children}</main>
    </>
  );
}
