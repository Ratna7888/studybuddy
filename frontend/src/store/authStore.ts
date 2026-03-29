import { create } from "zustand";
import { authAPI } from "@/services/api";
import type { AuthState } from "@/types";

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  token: null,
  isAuthenticated: false,

  loadFromStorage: () => {
    const token = localStorage.getItem("token");
    const userStr = localStorage.getItem("user");
    if (token && userStr) {
      set({
        token,
        user: JSON.parse(userStr),
        isAuthenticated: true,
      });
    }
  },

  register: async (email, name, password) => {
    const { data } = await authAPI.register(email, name, password);
    localStorage.setItem("token", data.access_token);
    localStorage.setItem("user", JSON.stringify(data.user));
    set({
      token: data.access_token,
      user: data.user,
      isAuthenticated: true,
    });
  },

  login: async (email, password) => {
    const { data } = await authAPI.login(email, password);
    localStorage.setItem("token", data.access_token);
    localStorage.setItem("user", JSON.stringify(data.user));
    set({
      token: data.access_token,
      user: data.user,
      isAuthenticated: true,
    });
  },

  logout: () => {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    set({ token: null, user: null, isAuthenticated: false });
  },
}));