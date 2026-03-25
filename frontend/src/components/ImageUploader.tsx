/**
 * Image Uploader Component
 *
 * Allows users to upload images (husband/wife photos)
 * Updated for Phase 1.5 API compatibility
 */

import React, { useState } from 'react';
import { Upload, Button, message, Image } from 'antd';
import { UploadOutlined, DeleteOutlined } from '@ant-design/icons';
import type { UploadFile } from 'antd/es/upload/interface';
import { apiClient, PhotoUploadResponse } from '../services/api';

interface ImageUploaderProps {
  onUploadComplete: (photoData: PhotoUploadResponse) => void;
  imageType: 'husband' | 'wife' | 'template';
  label?: string;
}

export const ImageUploader: React.FC<ImageUploaderProps> = ({
  onUploadComplete,
  imageType,
  label,
}) => {
  const [uploading, setUploading] = useState(false);
  const [uploadedPhoto, setUploadedPhoto] = useState<PhotoUploadResponse | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);

  const handleUpload = async (file: File) => {
    setUploading(true);

    try {
      // Create preview
      const reader = new FileReader();
      reader.onload = (e) => {
        setPreviewUrl(e.target?.result as string);
      };
      reader.readAsDataURL(file);

      // Upload to server using Phase 1.5 photo upload API
      const response = await apiClient.uploadPhoto(file);

      message.success(`${file.name} uploaded successfully!`);
      setUploadedPhoto(response);
      onUploadComplete(response);
    } catch (error: any) {
      message.error(`Upload failed: ${error.response?.data?.detail || error.message}`);
      setPreviewUrl(null);
    } finally {
      setUploading(false);
    }
  };

  const handleRemove = () => {
    setUploadedPhoto(null);
    setPreviewUrl(null);
  };

  const beforeUpload = (file: File) => {
    // Validate file type
    const isImage = file.type.startsWith('image/');
    if (!isImage) {
      message.error('You can only upload image files!');
      return Upload.LIST_IGNORE;
    }

    // Validate file size (10MB)
    const isLt10M = file.size / 1024 / 1024 < 10;
    if (!isLt10M) {
      message.error('Image must be smaller than 10MB!');
      return Upload.LIST_IGNORE;
    }

    // Trigger upload
    handleUpload(file);

    // Prevent default upload behavior
    return false;
  };

  return (
    <div style={{ marginBottom: 24 }}>
      <div style={{ marginBottom: 8, fontWeight: 500 }}>
        {label || `Upload ${imageType.charAt(0).toUpperCase() + imageType.slice(1)}'s Photo`}
      </div>

      {!uploadedPhoto ? (
        <Upload
          beforeUpload={beforeUpload}
          showUploadList={false}
          accept="image/*"
          disabled={uploading}
        >
          <Button
            icon={<UploadOutlined />}
            loading={uploading}
            size="large"
            type="dashed"
            style={{ width: '100%', height: 120 }}
          >
            {uploading ? 'Uploading...' : 'Click to Upload'}
          </Button>
        </Upload>
      ) : (
        <div style={{ position: 'relative', display: 'inline-block' }}>
          <Image
            src={previewUrl || ''}
            alt={uploadedPhoto.filename}
            width={200}
            style={{ borderRadius: 8 }}
          />
          <div style={{ marginTop: 8, fontSize: 12, color: '#666' }}>
            {uploadedPhoto.filename}
            <br />
            {uploadedPhoto.width} × {uploadedPhoto.height}
            <br />
            {(uploadedPhoto.file_size / 1024).toFixed(1)} KB
            {uploadedPhoto.storage_type === 'temporary' && (
              <>
                <br />
                <span style={{ color: '#faad14' }}>⏰ Temporary (24h)</span>
              </>
            )}
          </div>
          <Button
            danger
            size="small"
            icon={<DeleteOutlined />}
            onClick={handleRemove}
            style={{ marginTop: 8 }}
          >
            Remove
          </Button>
        </div>
      )}
    </div>
  );
};

export default ImageUploader;
