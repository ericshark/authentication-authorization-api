"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { CheckCircle2, X, XCircle } from "lucide-react";
import { apiRequest } from "@/lib/api";

const AuthContext = createContext(null);
const ToastContext = createContext(null);

export function AppProviders({ children }) {
  const [user, setUser] = useState(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [toasts, setToasts] = useState([]);

  const refreshUser = useCallback(async () => {
    setAuthLoading(true);
    try {
      const { data } = await apiRequest("/users/me");
      setUser(data);
      return data;
    } catch (error) {
      if (error.status === 401) setUser(null);
      return null;
    } finally {
      setAuthLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshUser();
  }, [refreshUser]);

  const toast = useCallback((message, tone = "success") => {
    const id = crypto.randomUUID();
    setToasts((current) => [...current, { id, message, tone }]);
    window.setTimeout(() => {
      setToasts((current) => current.filter((item) => item.id !== id));
    }, 4200);
  }, []);

  const removeToast = useCallback((id) => {
    setToasts((current) => current.filter((item) => item.id !== id));
  }, []);

  const authValue = useMemo(
    () => ({ user, setUser, authLoading, refreshUser }),
    [user, authLoading, refreshUser],
  );

  return (
    <AuthContext.Provider value={authValue}>
      <ToastContext.Provider value={toast}>
        {children}
        <div className="toast-stack" aria-live="polite">
          {toasts.map((item) => (
            <div className={`toast toast-${item.tone}`} key={item.id}>
              {item.tone === "error" ? <XCircle size={18} /> : <CheckCircle2 size={18} />}
              <span>{item.message}</span>
              <button aria-label="Dismiss notification" onClick={() => removeToast(item.id)}>
                <X size={16} />
              </button>
            </div>
          ))}
        </div>
      </ToastContext.Provider>
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}

export function useToast() {
  return useContext(ToastContext);
}
