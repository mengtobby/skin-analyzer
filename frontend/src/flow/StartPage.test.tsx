import '@testing-library/jest-dom/vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import { StartPage } from './StartPage';
afterEach(cleanup);
it('explains preparation, privacy and cosmetic guidance before starting', () => {
  const start = vi.fn(); render(<StartPage onStart={start} />);
  expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent("Let's take a look at your skin");
  expect(screen.getByText(/arm's length/)).toBeVisible();
  expect(screen.getByText(/never saved/)).toBeVisible();
  expect(screen.getByText('Cosmetic guidance only - not a medical diagnosis. Seek professional advice for persistent, painful or changing skin concerns.', { exact: true })).toBeVisible();
  fireEvent.click(screen.getByRole('button', { name: 'Start analyzing' })); expect(start).toHaveBeenCalledOnce();
});
