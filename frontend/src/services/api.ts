/**
 * API Client Service
 *
 * Provides methods for interacting with the backend API
 * Updated for Phase 1.5 API compatibility
 */

import axios, { AxiosInstance } from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const API_VERSION = '/api/v1';

// Generate or retrieve session ID for grouping temporary uploads
const getSessionId = (): string => {
  let sessionId = sessionStorage.getItem('faceswap_session_id');
  if (!sessionId) {
    sessionId = `session_${Date.now()}_${Math.random().toString(36).substring(7)}`;
    sessionStorage.setItem('faceswap_session_id', sessionId);
  }
  return sessionId;
};

// Phase 1.5: Updated interface for photo upload response
export interface PhotoUploadResponse {
  id: number;
  filename: string;
  storage_path: string;
  file_size: number;
  width: number;
  height: number;
  storage_type: string;
  session_id: string;
  expires_at: string;
  image_url: string;
}

// Phase 1.5: Updated Template interface
export interface Template {
  id: number;
  name: string;  // Changed from 'title' to 'name'
  description?: string;
  category: string;
  original_image_id: number;  // Changed from 'image_id'
  is_preprocessed: boolean;
  face_count: number;
  male_face_count: number;
  female_face_count: number;
  popularity_score: number;
  image_url: string;  // Generated from storage_path
  created_at: string;
}

// Phase 1.5: Templates list response
export interface TemplatesListResponse {
  templates: Template[];
  total: number;
}

// Phase 1.5: Updated FaceSwapRequest
export interface FaceSwapRequest {
  husband_photo_id: number;  // Changed from husband_image_id
  wife_photo_id: number;  // Changed from wife_image_id
  template_id: number;
  use_default_mapping?: boolean;
  use_preprocessed?: boolean;
}

// Phase 1.5: Updated FaceSwapResponse
export interface FaceSwapResponse {
  task_id: string;  // Changed from number to string
  status: string;
  created_at: string;
  message: string;
}

// Phase 1.5: Updated TaskStatus
export interface TaskStatus {
  task_id: string;  // Changed from number to string
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress: number;
  result_image_url?: string;
  processing_time?: number;
  error_message?: string;
  created_at: string;
  completed_at?: string;
  face_mappings?: any[];
}

class APIClient {
  private client: AxiosInstance;
  private sessionId: string;

  constructor() {
    this.client = axios.create({
      baseURL: `${API_BASE_URL}${API_VERSION}`,
      headers: {
        'Content-Type': 'application/json',
      },
    });
    this.sessionId = getSessionId();
  }

  /**
   * Upload a photo (Phase 1.5: Separated Upload APIs)
   * Photos are uploaded as temporary files with expiration
   */
  async uploadPhoto(file: File): Promise<PhotoUploadResponse> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('session_id', this.sessionId);

    const response = await this.client.post<PhotoUploadResponse>(
      '/photos/upload',
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );

    return response.data;
  }

  /**
   * Upload a template (Phase 1.5: Separated Upload APIs)
   * Templates are uploaded as permanent files
   */
  async uploadTemplate(
    file: File,
    name: string,
    category: string = 'custom',
    description?: string
  ): Promise<Template> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('name', name);
    formData.append('category', category);
    if (description) {
      formData.append('description', description);
    }

    const response = await this.client.post<Template>(
      '/templates/upload',
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );

    return response.data;
  }

  /**
   * Get list of templates (Phase 1.5: Updated endpoint)
   */
  async getTemplates(
    category?: string,
    limit: number = 20,
    offset: number = 0
  ): Promise<Template[]> {
    const params = new URLSearchParams();
    if (category && category !== 'all') {
      params.append('category', category);
    }
    params.append('limit', limit.toString());
    params.append('offset', offset.toString());

    const response = await this.client.get<TemplatesListResponse>(
      `/templates?${params.toString()}`
    );

    return response.data.templates;
  }

  /**
   * Create a face-swap task (Phase 1.5: Updated endpoint and fields)
   */
  async createFaceSwapTask(request: FaceSwapRequest): Promise<FaceSwapResponse> {
    const response = await this.client.post<FaceSwapResponse>(
      '/faceswap/swap',
      request
    );

    return response.data;
  }

  /**
   * Get task status (Phase 1.5: task_id is now string)
   */
  async getTaskStatus(taskId: string): Promise<TaskStatus> {
    const response = await this.client.get<TaskStatus>(
      `/faceswap/task/${taskId}`
    );

    return response.data;
  }

  /**
   * Get full image URL
   */
  getImageUrl(path: string): string {
    if (path.startsWith('http')) {
      return path;
    }
    return `${API_BASE_URL}${path}`;
  }

  /**
   * Check API health
   */
  async checkHealth(): Promise<any> {
    const response = await axios.get(`${API_BASE_URL}/health`);
    return response.data;
  }
}

// Export singleton instance
export const apiClient = new APIClient();
export default apiClient;
