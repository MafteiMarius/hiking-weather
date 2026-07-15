import { useEffect, useState } from "react";
import { Mountain, User, LogOut, Loader2 } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import { AuthModal } from "@/components/AuthModal";
import { LanguageToggle } from "@/components/LanguageToggle";
import { useMe, useLogout } from "@/features/auth/useAuth";

interface AppShellProps {
  children: React.ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  const [authOpen, setAuthOpen] = useState(false);
  const { data: me, isLoading: meLoading } = useMe();
  const logout = useLogout();
  const { t, i18n } = useTranslation();

  // Keep the document language in sync for accessibility and correct
  // hyphenation/spellcheck. Runs on mount and on every toggle.
  useEffect(() => {
    document.documentElement.lang = i18n.language;
  }, [i18n.language]);

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <header className="flex shrink-0 items-center justify-between border-b border-stone-200 bg-white px-4 h-12">
        <div className="flex items-center gap-2">
          <Mountain size={18} className="text-green-700" />
          <span className="text-sm font-semibold tracking-tight text-stone-900">
            HikeCast
          </span>
        </div>

        <div className="flex items-center gap-2">
          <LanguageToggle />
          {meLoading ? (
            <Loader2 size={16} className="animate-spin text-stone-400" />
          ) : me ? (
            <>
              <span className="hidden text-xs text-stone-500 sm:block">
                {me.email}
              </span>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => logout.mutate()}
                disabled={logout.isPending}
                aria-label={t("header.signOut")}
              >
                <LogOut size={14} />
                <span className="hidden sm:inline">{t("header.signOut")}</span>
              </Button>
            </>
          ) : (
            <Button
              variant="outline"
              size="sm"
              onClick={() => setAuthOpen(true)}
            >
              <User size={14} />
              {t("header.signIn")}
            </Button>
          )}
        </div>
      </header>

      {/* Page content */}
      <main className="flex-1 overflow-hidden">{children}</main>

      <AuthModal open={authOpen} onClose={() => setAuthOpen(false)} />
    </div>
  );
}
