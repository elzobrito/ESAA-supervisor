import axios from 'axios';

export const api = axios.create({
  baseURL: '/api/v1',
  timeout: 10000,
});

export function extractErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    return error.message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return 'Erro inesperado de API.';
}
