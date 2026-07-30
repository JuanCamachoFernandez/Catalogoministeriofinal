import type { SessionUser } from "../tipos";
import { api } from "../../../compartido/servicios/clienteHttp";

export type LoginResponse = {
  access_token: string;
  refresh_token: string;
  user: SessionUser;
};

export const servicioAutenticacion = {
  login: (login: string, password: string) =>
    api.post<LoginResponse>("/auth/login", { login, password }).then(({ data }) => data),
  me: () => api.get<SessionUser>("/auth/me").then(({ data }) => data),
  logout: (token: string) =>
    api.post("/auth/logout", {}, { headers: { Authorization: `Bearer ${token}` } }),
  reauthenticate: (password: string) =>
    api.post("/auth/reauthenticate", { current_password: password }),
  changePassword: (currentPassword: string, newPassword: string) =>
    api.post("/auth/change-password", {
      current_password: currentPassword,
      new_password: newPassword,
    }),
  requestRecoveryCode: (email: string) =>
    api.post("/auth/forgot-password", { email }),
  verifyRecoveryCode: (email: string, code: string) =>
    api
      .post<{ reset_token: string }>("/auth/verify-recovery-code", { email, code })
      .then(({ data }) => data),
  resetPassword: (token: string, newPassword: string) =>
    api
      .post<{ message: string }>("/auth/reset-password", {
        token,
        new_password: newPassword,
      })
      .then(({ data }) => data),
};
