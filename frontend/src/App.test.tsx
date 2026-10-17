import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import App from "./App";
import { frameFixture, reportFixture } from './protocol/fixtures';
const mocks = vi.hoisted(() => ({ reset: vi.fn(), clear: vi.fn() }));
vi.mock('./stream/useSkinStream', () => ({ useSkinStream: () => ({
  bitmapRef: { current: null }, headerRef: { current: null }, displayHeaderRef: { current: null },
  header: null, report: null, health: null, connection: 'connected', error: null,
  sendReset: mocks.reset, clearReport: mocks.clear,
}) }));
vi.mock('./flow/CameraPage', () => ({ CameraPage: ({ onCapture }: { onCapture: (s: unknown) => void }) =>
  <button onClick={() => onCapture({ image: document.createElement('canvas'), header: frameFixture, report: reportFixture, width: 1280, height: 720, capturedAt: 0 })}>Capture test image</button> }));
vi.mock('./settings/SettingsPage', () => ({ SettingsPage: ({ onInputChanged }: { onInputChanged: () => void }) => <button onClick={onInputChanged}>Change input</button> }));
vi.mock('./flow/ResultsPage', () => ({ ResultsPage: ({ onContinue }: { onContinue: () => void }) => <button onClick={onContinue}>See treatments</button> }));
afterEach(() => { cleanup(); history.replaceState(null, '', '/'); vi.clearAllMocks(); });
it('opens Start and navigates to the Camera step', () => {
  render(<App />); expect(screen.getByRole('heading', { name: /take a look/ })).toBeVisible();
  fireEvent.click(screen.getByRole('button', { name: 'Start analyzing' }));
  expect(location.hash).toBe('#camera');
  expect(screen.getByText('Camera', { selector: '.ui-stepper__label' }).closest('li')).toHaveAttribute('aria-current', 'step');
});
it.each(['results', 'treatments'])('redirects direct #%s visits', route => {
  history.replaceState(null, '', `/#${route}`); render(<App />);
  expect(screen.getByRole('heading', { name: /take a look/ })).toBeVisible();
});
it('opens Settings via header navigation and accepts the settings hash', async () => {
  render(<App />); fireEvent.click(screen.getByRole('link', { name: 'Settings' }));
  expect(await screen.findByRole('button', { name: 'Change input' })).toBeVisible();
  expect(screen.getByRole('link', { name: 'Settings' })).toHaveAttribute('aria-current', 'page');
  fireEvent.click(screen.getByRole('button', { name: 'Change input' })); expect(mocks.clear).toHaveBeenCalledOnce();
});
it('opens a legacy settings bookmark', async () => {
  history.replaceState(null, '', '/#settings'); render(<App />);
  expect(await screen.findByRole('button', { name: 'Change input' })).toBeVisible();
});
it('restarts from treatments, clearing report and resetting tracking', () => {
  render(<App />); fireEvent.click(screen.getByRole('button', { name: 'Start analyzing' }));
  fireEvent.click(screen.getByRole('button', { name: 'Capture test image' }));
  fireEvent.click(screen.getByRole('button', { name: 'See treatments' }));
  fireEvent.click(screen.getByRole('button', { name: 'Start a new analysis' }));
  expect(mocks.reset).toHaveBeenCalledOnce(); expect(mocks.clear).toHaveBeenCalledOnce();
  expect(screen.getByRole('heading', { name: /take a look/ })).toBeVisible();
});
