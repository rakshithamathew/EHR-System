import axios from "axios";

const configuredBaseUrl = import.meta.env.VITE_API_BASE_URL?.trim();

export const apiClient = axios.create({
  baseURL: configuredBaseUrl
    ? configuredBaseUrl.replace(/\/+$/, "")
    : undefined,
  headers: {
    Accept: "application/json",
  },
});
