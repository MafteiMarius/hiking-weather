import { useState } from "react";
import { isAxiosError } from "axios";
import { Dialog } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useLogin, useRegister } from "@/features/auth/useAuth";
import { cn } from "@/lib/utils";

// fastapi-users signals errors with machine-readable codes in `detail`:
// either a plain string ("REGISTER_USER_ALREADY_EXISTS") or an object
// ({ code: "REGISTER_INVALID_PASSWORD", reason: "..." }). Map both to
// something a human can act on.
function registerErrorMessage(err: unknown): string {
  if (isAxiosError(err)) {
    const detail = err.response?.data?.detail;
    if (detail === "REGISTER_USER_ALREADY_EXISTS") {
      return "An account with this email already exists. Try signing in instead.";
    }
    if (typeof detail?.reason === "string") {
      return detail.reason; // password policy failure, worded by the backend
    }
    if (err.response?.status === 422) {
      return "That doesn't look like a valid email address.";
    }
    if (!err.response) {
      return "Could not reach the server — is the backend running?";
    }
  }
  return "Registration failed. Please try again.";
}

function loginErrorMessage(err: unknown): string {
  if (isAxiosError(err) && !err.response) {
    return "Could not reach the server — is the backend running?";
  }
  return "Invalid email or password.";
}

interface AuthModalProps {
  open: boolean;
  onClose: () => void;
}

type Tab = "login" | "register";

export function AuthModal({ open, onClose }: AuthModalProps) {
  const [tab, setTab] = useState<Tab>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [formError, setFormError] = useState<string | null>(null);

  const login = useLogin();
  const register = useRegister();

  const isPending = login.isPending || register.isPending;

  function reset() {
    setEmail("");
    setPassword("");
    setConfirm("");
    setFormError(null);
    login.reset();
    register.reset();
  }

  function switchTab(t: Tab) {
    setTab(t);
    reset();
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setFormError(null);

    if (tab === "register") {
      if (password !== confirm) {
        setFormError("Passwords do not match.");
        return;
      }
      if (password.length < 8) {
        setFormError("Password must be at least 8 characters.");
        return;
      }
      try {
        await register.mutateAsync({ email, password });
        // Auto-login after registration
        await login.mutateAsync({ email, password });
        reset();
        onClose();
      } catch (err) {
        setFormError(registerErrorMessage(err));
      }
      return;
    }

    try {
      await login.mutateAsync({ email, password });
      reset();
      onClose();
    } catch (err) {
      setFormError(loginErrorMessage(err));
    }
  }

  return (
    <Dialog open={open} onClose={onClose} title="HikeCast">
      {/* Tabs */}
      <div className="mb-5 flex rounded-lg border border-stone-200 bg-stone-50 p-1">
        {(["login", "register"] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => switchTab(t)}
            className={cn(
              "flex-1 rounded-md py-1.5 text-sm font-medium capitalize transition-colors",
              tab === t
                ? "bg-white text-stone-900 shadow-sm"
                : "text-stone-500 hover:text-stone-700",
            )}
          >
            {t === "login" ? "Sign in" : "Create account"}
          </button>
        ))}
      </div>

      <form onSubmit={handleSubmit} className="space-y-3">
        <div>
          <label className="mb-1 block text-xs font-medium text-stone-600">
            Email
          </label>
          <Input
            type="email"
            autoComplete="email"
            required
            placeholder="you@example.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-stone-600">
            Password
          </label>
          <Input
            type="password"
            autoComplete={tab === "login" ? "current-password" : "new-password"}
            required
            placeholder="••••••••"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </div>
        {tab === "register" && (
          <div>
            <label className="mb-1 block text-xs font-medium text-stone-600">
              Confirm password
            </label>
            <Input
              type="password"
              autoComplete="new-password"
              required
              placeholder="••••••••"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
            />
          </div>
        )}

        {formError && (
          <p className="text-sm text-red-600">{formError}</p>
        )}

        <Button type="submit" className="mt-2 w-full" disabled={isPending}>
          {isPending
            ? "Please wait…"
            : tab === "login"
              ? "Sign in"
              : "Create account"}
        </Button>
      </form>

      <p className="mt-4 text-center text-xs text-stone-500">
        {tab === "login" ? (
          <>
            No account?{" "}
            <button
              onClick={() => switchTab("register")}
              className="font-medium text-green-700 hover:underline"
            >
              Sign up
            </button>
          </>
        ) : (
          <>
            Already have one?{" "}
            <button
              onClick={() => switchTab("login")}
              className="font-medium text-green-700 hover:underline"
            >
              Sign in
            </button>
          </>
        )}
      </p>
    </Dialog>
  );
}
