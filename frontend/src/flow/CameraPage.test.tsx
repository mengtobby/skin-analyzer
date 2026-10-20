import "@testing-library/jest-dom/vitest";
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { CameraPage } from "./CameraPage";
import { frameFixture, qualityFixture, reportFixture } from "../protocol/fixtures";
import type { SkinStream } from "./useScan";
import { readFileSync } from "node:fs";
import { URL as NodeURL } from "node:url";
const flowCss = readFileSync(new NodeURL("./flow.css", import.meta.url), "utf-8");
vi.mock('../components/LiveView', () => ({ LiveView: () => <div>Live camera</div> }));
function stream(): SkinStream {
  const header = { ...frameFixture, quality: { ...qualityFixture, ok: true, issues: [] } };
  return { header, headerRef: { current: header }, displayHeaderRef: { current: header },
    bitmapRef: { current: {} as ImageBitmap }, report: reportFixture, health: null,
    connection: 'connected', error: null, sendReset: vi.fn(), clearReport: vi.fn() };
}
beforeEach(() => {
  vi.useFakeTimers();
  vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue({ drawImage: vi.fn() } as unknown as CanvasRenderingContext2D);
});
afterEach(() => { cleanup(); vi.useRealTimers(); vi.restoreAllMocks(); });
it('requires connection, face and passing quality', () => {
  const s = stream(); const onCapture = vi.fn();
  const { rerender } = render(<CameraPage stream={{ ...s, connection: 'connecting' }} onCapture={onCapture} />);
  const button = () => screen.getByRole('button', { name: 'Analyze my skin' });
  expect(button()).toBeDisabled();
  rerender(<CameraPage stream={{ ...s, header: { ...s.header!, face: null } }} onCapture={onCapture} />);
  expect(button()).toBeDisabled();
  expect(screen.getByText('Camera connected - 25 fps', { exact: true })).toBeVisible();
  expect(screen.getByText('No face detected - centre your face in the camera.', { exact: true })).toBeVisible();
  expect(screen.getByRole('status')).toContainElement(screen.getByText('No face detected - centre your face in the camera.', { exact: true }));
  rerender(<CameraPage stream={{ ...s, header: { ...s.header!, quality: qualityFixture } }} onCapture={onCapture} />);
  expect(button()).toBeDisabled(); expect(screen.getByText('Too dark - face a window or lamp')).toBeVisible();
  rerender(<CameraPage stream={s} onCapture={onCapture} />); expect(button()).toBeEnabled();
});
it('counts down and captures using a report received after starting', () => {
  const s = stream(); const onCapture = vi.fn();
  const { rerender } = render(<CameraPage stream={s} onCapture={onCapture} />);
  fireEvent.click(screen.getByRole('button', { name: 'Analyze my skin' }));
  act(() => vi.advanceTimersByTime(1000)); expect(screen.getByText('Hold still... 2 seconds', { exact: true })).toBeVisible();
  const fresh = { ...reportFixture, disclaimer: 'Fresh report' };
  rerender(<CameraPage stream={{ ...s, report: fresh }} onCapture={onCapture} />);
  act(() => vi.advanceTimersByTime(2000));
  expect(onCapture).toHaveBeenCalledOnce(); expect(onCapture.mock.calls[0][0].report.disclaimer).toBe('Fresh report');
});
it('waits for a fresh report and falls back after three more seconds', () => {
  const onCapture = vi.fn(); render(<CameraPage stream={stream()} onCapture={onCapture} />);
  fireEvent.click(screen.getByRole('button', { name: 'Analyze my skin' }));
  act(() => vi.advanceTimersByTime(3000)); expect(onCapture).not.toHaveBeenCalled();
  act(() => vi.advanceTimersByTime(3000)); expect(onCapture).toHaveBeenCalledOnce();
});
it('aborts after losing the face for more than 1.5 seconds', () => {
  const s = stream(); const onCapture = vi.fn(); render(<CameraPage stream={s} onCapture={onCapture} />);
  fireEvent.click(screen.getByRole('button', { name: 'Analyze my skin' }));
  s.headerRef.current = { ...s.header!, face: null };
  act(() => vi.advanceTimersByTime(1700));
  expect(screen.getByRole('alert')).toHaveTextContent('lost a clear view'); expect(onCapture).not.toHaveBeenCalled();
});
it('shows a friendly error if no report arrives', () => {
  const onCapture = vi.fn(); render(<CameraPage stream={{ ...stream(), report: null }} onCapture={onCapture} />);
  fireEvent.click(screen.getByRole('button', { name: 'Analyze my skin' }));
  act(() => vi.advanceTimersByTime(6000));
  expect(screen.getByRole('alert')).toHaveTextContent('could not finish'); expect(onCapture).not.toHaveBeenCalled();
});
it('cancels without capturing', () => {
  const onCapture = vi.fn(); render(<CameraPage stream={stream()} onCapture={onCapture} />);
  fireEvent.click(screen.getByRole('button', { name: 'Analyze my skin' }));
  fireEvent.click(screen.getByRole('button', { name: 'Cancel scan' }));
  act(() => vi.advanceTimersByTime(7000)); expect(onCapture).not.toHaveBeenCalled();
});
it('shows friendly guidance for every quality issue', () => {
  const messages = {
    too_dark: 'Too dark - face a window or lamp',
    too_bright: 'Too bright - reduce direct light',
    uneven_light: 'Uneven lighting - light your face from the front',
    too_far: 'Move closer to the camera', turned_away: 'Face the camera',
    tilted: 'Level your head', occluded: 'Clear hair or hands away from your face',
  };
  const s = stream();
  render(<CameraPage stream={{ ...s, header: { ...s.header!, quality: { ...qualityFixture, issues: Object.keys(messages) } } }} onCapture={vi.fn()} />);
  Object.values(messages).forEach(message => expect(screen.getByText(message)).toBeVisible());
  expect(screen.getByText('Quality 30%')).toBeVisible();
});
it('aborts when quality stays poor', () => {
  const s = stream(); const onCapture = vi.fn(); render(<CameraPage stream={s} onCapture={onCapture} />);
  fireEvent.click(screen.getByRole('button', { name: 'Analyze my skin' }));
  s.headerRef.current = { ...s.header!, quality: qualityFixture };
  act(() => vi.advanceTimersByTime(1700));
  expect(screen.getByRole('alert')).toHaveTextContent('lost a clear view'); expect(onCapture).not.toHaveBeenCalled();
});

it.each([false, true])('pairs snapshot pixels with the decoded header (fallback: %s)', fallback => {
  const s = stream(); const onCapture = vi.fn();
  const displayed = s.displayHeaderRef.current!;
  s.headerRef.current = { ...displayed, frame_id: displayed.frame_id + 1, tracks: [] };
  render(<CameraPage stream={s} onCapture={onCapture} />);
  fireEvent.click(screen.getByRole('button', { name: 'Analyze my skin' }));
  act(() => vi.advanceTimersByTime(5900));
  if (fallback) s.bitmapRef.current = null;
  act(() => vi.advanceTimersByTime(100));
  expect(onCapture).toHaveBeenCalledOnce();
  expect(onCapture.mock.calls[0][0].header).toEqual(displayed);
  expect(onCapture.mock.calls[0][0].header).not.toEqual(s.headerRef.current);
});
it('resets the reported progress when a scan aborts', () => {
  const s = stream(); const onProgress = vi.fn();
  render(<CameraPage stream={s} onCapture={vi.fn()} onProgress={onProgress} />);
  fireEvent.click(screen.getByRole('button', { name: 'Analyze my skin' }));
  act(() => vi.advanceTimersByTime(500));
  expect(onProgress).toHaveBeenLastCalledWith(expect.any(Number));
  expect(onProgress.mock.lastCall![0]).toBeGreaterThan(0);
  s.headerRef.current = { ...s.header!, face: null };
  act(() => vi.advanceTimersByTime(1700));
  expect(screen.getByRole('alert')).toHaveTextContent('lost a clear view');
  expect(onProgress).toHaveBeenLastCalledWith(0);
});
it('copies a frame only when a new frame arrives, into one reused canvas', () => {
  const s = stream(); const create = vi.spyOn(document, 'createElement');
  render(<CameraPage stream={s} onCapture={vi.fn()} />);
  fireEvent.click(screen.getByRole('button', { name: 'Analyze my skin' }));
  const canvases = () => create.mock.calls.filter(([tag]) => tag === 'canvas').length;
  act(() => vi.advanceTimersByTime(1000));
  expect(canvases()).toBe(1);
  const next = { ...s.header!, frame_id: s.header!.frame_id + 1 };
  s.headerRef.current = next; s.displayHeaderRef.current = next;
  act(() => vi.advanceTimersByTime(1000));
  expect(canvases()).toBe(1);
});
it('keeps guidance and error regions mounted while scores and fps change', () => {
  const s = stream();
  const { rerender } = render(<CameraPage stream={s} onCapture={vi.fn()} />);
  const guidance = screen.getByRole('status');
  const alert = screen.getByRole('alert');
  expect(alert).toBeEmptyDOMElement();
  rerender(<CameraPage stream={{ ...s, header: { ...s.header!, quality: qualityFixture }, error: 'Stream unavailable' }} onCapture={vi.fn()} />);
  expect(screen.getByRole('status')).toBe(guidance);
  expect(guidance).toHaveTextContent('Too dark - face a window or lamp');
  expect(guidance).not.toHaveTextContent(/Quality|fps/);
  expect(screen.getByRole('alert')).toBe(alert);
  expect(alert).toHaveTextContent('Stream unavailable');
  expect(screen.getAllByRole('status')).toHaveLength(1);
});

it('focuses Cancel during scanning and Analyze after cancelling or an error', () => {
  const s = stream();
  const { rerender } = render(<CameraPage stream={s} onCapture={vi.fn()} />);
  fireEvent.click(screen.getByRole('button', { name: 'Analyze my skin' }));
  expect(screen.getByRole('button', { name: 'Cancel scan' })).toHaveFocus();
  fireEvent.click(screen.getByRole('button', { name: 'Cancel scan' }));
  expect(screen.getByRole('button', { name: 'Analyze my skin' })).toHaveFocus();
  fireEvent.click(screen.getByRole('button', { name: 'Analyze my skin' }));
  const poor = { ...s.header!, face: null };
  s.headerRef.current = poor;
  rerender(<CameraPage stream={{ ...s, header: poor }} onCapture={vi.fn()} />);
  act(() => vi.advanceTimersByTime(1700));
  const analyze = screen.getByRole('button', { name: 'Analyze my skin' });
  expect(analyze).toHaveFocus();
  expect(analyze).toHaveAttribute('aria-disabled', 'true');
  expect(analyze.matches('.camera-page .ui-button[aria-disabled="true"]')).toBe(true);
  expect(flowCss).toMatch(/\.camera-page \.ui-button\[aria-disabled="true"\]\s*\{[^}]*opacity:\s*\.5;[^}]*cursor:\s*not-allowed;/);
  expect(flowCss).toMatch(/\.camera-page \.ui-button--primary\[aria-disabled="true"\]:hover\s*\{[^}]*background:\s*var\(--text\);[^}]*border-color:\s*var\(--text\);/);
  fireEvent.click(analyze);
  expect(screen.queryByRole('button', { name: 'Cancel scan' })).not.toBeInTheDocument();
});

it('changes the countdown text no more than once per second in the same polite region', () => {
  render(<CameraPage stream={stream()} onCapture={vi.fn()} />);
  const guidance = screen.getByRole('status');
  fireEvent.click(screen.getByRole('button', { name: 'Analyze my skin' }));
  expect(guidance).toHaveTextContent('Hold still... 3 seconds');
  act(() => vi.advanceTimersByTime(900));
  expect(guidance).toHaveTextContent('Hold still... 3 seconds');
  act(() => vi.advanceTimersByTime(100));
  expect(guidance).toHaveTextContent('Hold still... 2 seconds');
  expect(screen.getByRole('status')).toBe(guidance);
});
