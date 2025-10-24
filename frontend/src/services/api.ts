/**
 * API Client Service
 *
 * Provides methods for interacting with the backend API
 */

import axios, { AxiosInstance } from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const API_VERSION = '/api/v1';

export interface ImageUploadResponse {
  image_id: number;
  filename: string;
  storage_path: string;
  file_size: number;
  width: number;
  height: number;
}

export interface Template {
  id: number;
  title: string;
  image_url: string;
  category: string;
  face_count: number;
  popularity_score: number;
}

export interface FaceSwapRequest {
  husband_image_id: number;
  wife_image_id: number;
  template_id: number;
}

export interface FaceSwapResponse {
  task_id: number;
  status: string;
  created_at: string;
}

export interface TaskStatus {
  task_id: number;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress: number;
  result_image_url?: string;
  processing_time?: number;
  error_message?: string;
  created_at: string;
  completed_at?: string;
}

class APIClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: `${API_BASE_URL}${API_VERSION}`,
      headers: {
        'Content-Type': 'application/json',
      },
    });
  }

  /**
   * Upload an image file
   */
  async uploadImage(file: File, imageType: 'source' | 'template' | 'result'): Promise<ImageUploadResponse> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await this.client.post<ImageUploadResponse>(
      `/faceswap/upload-image?image_type=${imageType}`,
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
   * Get list of templates
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

    const response = await this.client.get<Template[]>(
      `/faceswap/templates?${params.toString()}`
    );

    return response.data;
  }

  /**
   * Create a face-swap task
   */
  async createFaceSwapTask(request: FaceSwapRequest): Promise<FaceSwapResponse> {
    const response = await this.client.post<FaceSwapResponse>(
      '/faceswap/swap-faces',
      request
    );

    return response.data;
  }

  /**
   * Get task status
   */
  async getTaskStatus(taskId: number): Promise<TaskStatus> {
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
