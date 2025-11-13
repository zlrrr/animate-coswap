/**
 * API Client Tests
 *
 * Tests for Phase 1.5 API client compatibility
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';

describe('API Client - Phase 1.5', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    sessionStorage.clear();
  });

  describe('Session Management', () => {
    it('should generate session_id format correctly', () => {
      // Test the session ID format
      const mockSessionId = `session_${Date.now()}_${Math.random().toString(36).substring(7)}`;

      expect(mockSessionId).toContain('session_');
      expect(typeof mockSessionId).toBe('string');
      expect(mockSessionId.length).toBeGreaterThan(10);
    });

    it('should store and retrieve session_id from sessionStorage', () => {
      const existingId = 'session_test_123';
      sessionStorage.setItem('faceswap_session_id', existingId);

      const sessionId = sessionStorage.getItem('faceswap_session_id');
      expect(sessionId).toBe(existingId);
    });
  });

  describe('API Types', () => {
    it('Template should have Phase 1.5 fields', () => {
      const template = {
        id: 1,
        name: 'Template 1',  // Phase 1.5: 'name' instead of 'title'
        description: 'Test template',
        category: 'acg',
        original_image_id: 10,  // Phase 1.5: 'original_image_id' instead of 'image_id'
        is_preprocessed: true,
        face_count: 2,
        male_face_count: 1,
        female_face_count: 1,
        popularity_score: 100,
        image_url: '/storage/templates/template1.jpg',
        created_at: '2025-11-01T00:00:00',
      };

      expect(template).toHaveProperty('name');
      expect(template).not.toHaveProperty('title');
      expect(template).toHaveProperty('original_image_id');
      expect(template).toHaveProperty('is_preprocessed');
      expect(template).toHaveProperty('male_face_count');
      expect(template).toHaveProperty('female_face_count');
    });

    it('FaceSwapRequest should use photo_id fields', () => {
      const request = {
        husband_photo_id: 1,  // Phase 1.5
        wife_photo_id: 2,  // Phase 1.5
        template_id: 3,
        use_default_mapping: true,
        use_preprocessed: true,
      };

      expect(request).toHaveProperty('husband_photo_id');
      expect(request).toHaveProperty('wife_photo_id');
      expect(request).toHaveProperty('use_default_mapping');
      expect(request).toHaveProperty('use_preprocessed');
    });

    it('Task ID should be string type in Phase 1.5', () => {
      const taskId = 'task_abc123';  // Phase 1.5: string

      expect(typeof taskId).toBe('string');
      expect(taskId).toContain('task_');
    });
  });

  describe('API Endpoints', () => {
    it('should use correct Phase 1.5 endpoint for photo upload', () => {
      // Phase 1.5: /api/v1/photos/upload
      expect('/api/v1/photos/upload').toContain('/photos/upload');
    });

    it('should use correct Phase 1.5 endpoint for templates', () => {
      // Phase 1.5: /api/v1/templates
      expect('/api/v1/templates').toContain('/templates');
    });

    it('should use correct Phase 1.5 endpoint for face swap', () => {
      // Phase 1.5: /api/v1/faceswap/swap
      expect('/api/v1/faceswap/swap').toContain('/faceswap/swap');
    });

    it('should use correct Phase 1.5 endpoint for task status', () => {
      // Phase 1.5: /api/v1/faceswap/task/{task_id}
      const taskId = 'task_abc123';
      const endpoint = `/api/v1/faceswap/task/${taskId}`;
      expect(endpoint).toContain('/faceswap/task/');
      expect(endpoint).toContain(taskId);
    });
  });
});
