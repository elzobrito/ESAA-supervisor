import axios from 'axios';

export const api = axios.create({
  baseURL: '/api/v1',
  timeout: 10000,
});

export function extractErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === 'string' && detail.trim()) {
      return detail;
    }
    if (detail && typeof detail === 'object') {
      const message = 'message' in detail && typeof detail.message === 'string' ? detail.message : null;
      const reasons = 'reasons' in detail && Array.isArray(detail.reasons) ? detail.reasons.filter((item: unknown): item is string => typeof item === 'string') : [];
      if (message && reasons.length > 0) {
        return `${message}: ${reasons.join(' | ')}`;
      }
      if (message) {
        return message;
      }
      if (reasons.length > 0) {
        return reasons.join(' | ');
      }
    }
    return error.message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return 'Erro inesperado de API.';
}
