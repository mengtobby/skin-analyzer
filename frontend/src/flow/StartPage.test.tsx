import '@testing-library/jest-dom/vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import { StartPage } from './StartPage';
afterEach(cleanup);
it('draws the mesh directly on a single card without an inner panel', () => {
  const { container } = render(<StartPage onStart={vi.fn()} />);
  const cards = container.querySelectorAll('.mesh-face-card');
  expect(cards).toHaveLength(1);
  const card = cards[0];
  expect(card.parentElement).toHaveClass('start-hero');
  expect(card.querySelector(':scope > svg')).toBeInTheDocument();
  expect(card.querySelector('rect, [class*="panel"], [class*="card"]')).not.toBeInTheDocument();
  expect(Array.from(card.children).every(child => child.tagName.toLowerCase() === 'svg' || child.classList.contains('ui-floating-badge'))).toBe(true);
});
it('draws a decorative face with an oval and distinct facial landmarks', () => {
  render(<StartPage onStart={vi.fn()} />);
  const illustration = document.querySelector('.mesh-face-card');
  expect(illustration).toHaveAttribute('aria-hidden', 'true');
  expect(illustration?.querySelector('svg')).toHaveAttribute('focusable', 'false');
  for (const name of ['face-oval', 'left-brow', 'right-brow', 'left-eye', 'right-eye', 'nose', 'lips']) {
    const group = illustration?.querySelector(`[data-landmark="${name}"]`);
    expect(group).toBeInTheDocument();
    expect(group?.querySelector('line, polyline')).toBeInTheDocument();
    expect(name === 'face-oval' ? group : group?.querySelector('polyline')).toHaveAttribute('stroke-dasharray', name === 'face-oval' ? '2 5' : '2 3');
    if (name !== 'face-oval') expect(group?.querySelectorAll('circle').length).toBeGreaterThan(3);
  }
  expect(illustration?.querySelectorAll('.ui-floating-badge')).toHaveLength(4);
});
it('explains preparation, privacy and cosmetic guidance before starting', () => {
  const start = vi.fn(); render(<StartPage onStart={start} />);
  expect(screen.getByRole('heading', { level: 1, name: "Let's take a look at your skin" })).toBeVisible();
  expect(document.querySelector('.mesh-face-card')).toHaveAttribute('aria-hidden', 'true');
  expect(screen.getByRole('button', { name: 'Start analyzing' })).toHaveClass('ui-button--cta');
  expect(screen.getByText(/arm's length/)).toBeVisible();
  expect(screen.getByText(/never saved/)).toBeVisible();
  expect(screen.getByText('Cosmetic guidance only - not a medical diagnosis. Seek professional advice for persistent, painful or changing skin concerns.', { exact: true })).toBeVisible();
  fireEvent.click(screen.getByRole('button', { name: 'Start analyzing' })); expect(start).toHaveBeenCalledOnce();
});
