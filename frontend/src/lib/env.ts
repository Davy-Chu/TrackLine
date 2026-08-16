const defaultApiBaseUrl = "http://localhost:8000";

export function resolveApiBaseUrl(value: string | undefined): string {
  return value?.trim() || defaultApiBaseUrl;
}

export const apiBaseUrl = resolveApiBaseUrl(process.env.NEXT_PUBLIC_API_URL);
