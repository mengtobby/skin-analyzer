import { act, cleanup, renderHook } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import { useAnalysisFlow } from './useAnalysisFlow';
import { frameFixture, reportFixture } from '../protocol/fixtures';
import type { AnalysisSnapshot } from './snapshot';
afterEach(() => { cleanup(); history.replaceState(null, '', '/'); });
export function snapshot(): AnalysisSnapshot {
  return { image: document.createElement('canvas'), width: 1280, height: 720, header: frameFixture, report: reportFixture, capturedAt: 0 };
}
it('defaults to start and navigates by hash', () => {
  const { result } = renderHook(useAnalysisFlow);
  expect(result.current.route).toBe('start');
  act(() => result.current.go('camera')); expect(location.hash).toBe('#camera');
  expect(result.current.route).toBe('camera');
});
it.each(['results', 'treatments'])('redirects %s without a capture', route => {
  history.replaceState(null, '', `/#${route}`);
  const { result } = renderHook(useAnalysisFlow);
  expect(result.current.route).toBe('start'); expect(location.hash).toBe('#start');
});
it('preserves the capture when revisiting earlier steps and clears it on restart', () => {
  const reset = vi.fn(); window.addEventListener('analysis-restart', reset);
  const { result } = renderHook(useAnalysisFlow); const captured = snapshot();
  act(() => { result.current.setSnapshot(captured); result.current.go('results'); });
  expect(result.current.route).toBe('results');
  act(() => result.current.go('start')); expect(result.current.snapshot).toBe(captured);
  act(() => result.current.go('camera')); expect(result.current.snapshot).toBe(captured);
  act(() => result.current.restart()); expect(result.current.snapshot).toBeNull();
  expect(result.current.route).toBe('start'); expect(reset).toHaveBeenCalledOnce();
  window.removeEventListener('analysis-restart', reset);
});
it('responds to browser navigation and accepts settings', () => {
  const { result } = renderHook(useAnalysisFlow);
  act(() => { history.replaceState(null, '', '/#settings'); window.dispatchEvent(new Event('hashchange')); });
  expect(result.current.route).toBe('settings');
});
