import { useState } from "react";
import { Mountain, User, LogOut, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { AuthModal } from "@/components/AuthModal";
import { useMe, useLogout } from "@/features/auth/useAuth";

interface AppShellProps {
  children: React.ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  const [authOpen, setAuthOpen] = useState(false);
  const { data: me, isLoading: meLoading } = useMe();
  const logout = useLogout();

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <header className="flex shrink-0 items-center justify-between border-b border-slate-700 bg-slate-900 px-4 h-12">
        <div className="flex items-center gap-2">
          <Mountain size={18} className="text-sky-400" />
          <span className="text-sm font-semibold tracking-tight text-slate-100">
            HikeCast
          </span>
        </div>

        <div className="flex items-center gap-2">
          {meLoading ? (
            <Loader2 size={16} className="animate-spin text-slate-400" />
          ) : me ? (
            <>
              <span className="hidden text-xs text-slate-400 sm:block">
                {me.email}
              </span>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => logout.mutate()}
                disabled={logout.isPending}
                aria-label="Sign out"
              >
                <LogOut size={14} />
                <span className="hidden sm:inline">Sign out</span>
              </Button>
            </>
          ) : (
            <Button
              variant="outline"
              size="sm"
              onClick={() => setAuthOpen(true)}
            >
              <User size={14} />
              Sign in
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
