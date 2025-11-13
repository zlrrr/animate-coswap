/**
 * Test Setup
 *
 * Global test configuration and mocks
 */

import '@testing-library/jest-dom';
import { beforeAll, afterEach, afterAll, vi } from 'vitest';

// Mock matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});

// Mock IntersectionObserver
global.IntersectionObserver = class IntersectionObserver {
  constructor() {}
  disconnect() {}
  observe() {}
  takeRecords() {
    return [];
  }
  unobserve() {}
} as any;

beforeAll(() => {
  // Setup before all tests
});

afterEach(() => {
  // Clear mocks after each test
  vi.clearAllMocks();
  // Clear storage
  sessionStorage.clear();
  localStorage.clear();
});

afterAll(() => {
  // Cleanup after all tests
});
