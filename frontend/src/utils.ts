import type { PipelineParams } from './types';

export function fmtSize(bytes: number): string {
  if (bytes > 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  return `${(bytes / 1024).toFixed(0)} KB`;
}

export function fmtDate(iso: string): string {
  return new Date(iso).toLocaleString('ko-KR');
}

export function fmtParams(params?: PipelineParams | null): string | null {
  if (!params) return null;
  const parts = [
    `삼각형 비율: ${Math.round(params.tris_ratio * 100)}%`,
    `텍스쳐 비율: ${Math.round(params.texture_ratio * 100)}%`
  ];
  if (params.target_tris) parts.push(`${params.target_tris.toLocaleString()} tris`);
  if (params.texture_size) parts.push(`${params.texture_size}px`);
  if (params.skip_high_poly_cleanup) parts.push('cleanup skip');
  if (params.skip_cage) parts.push('cage skip');
  return parts.join(' · ');
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
