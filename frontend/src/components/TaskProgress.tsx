/**
 * Task Progress Component
 *
 * Displays real-time progress of face-swap task
 * Updated for Phase 1.5 API compatibility
 */

import React, { useEffect, useState } from 'react';
import { Progress, Card, Spin, Result, Button, Image } from 'antd';
import {
  LoadingOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  DownloadOutlined,
} from '@ant-design/icons';
import { apiClient, TaskStatus } from '../services/api';

interface TaskProgressProps {
  taskId: string;  // Changed from number to string for Phase 1.5
  onComplete?: (task: TaskStatus) => void;
  onError?: (error: string) => void;
}

export const TaskProgress: React.FC<TaskProgressProps> = ({
  taskId,
  onComplete,
  onError,
}) => {
  const [task, setTask] = useState<TaskStatus | null>(null);
  const [polling, setPolling] = useState(true);

  useEffect(() => {
    let intervalId: NodeJS.Timeout;

    const pollTaskStatus = async () => {
      try {
        const status = await apiClient.getTaskStatus(taskId);
        setTask(status);

        if (status.status === 'completed') {
          setPolling(false);
          onComplete?.(status);
        } else if (status.status === 'failed') {
          setPolling(false);
          onError?.(status.error_message || 'Unknown error');
        }
      } catch (error: any) {
        console.error('Error polling task status:', error);
      }
    };

    // Initial poll
    pollTaskStatus();

    // Poll every 2 seconds
    if (polling) {
      intervalId = setInterval(pollTaskStatus, 2000);
    }

    return () => {
      if (intervalId) {
        clearInterval(intervalId);
      }
    };
  }, [taskId, polling, onComplete, onError]);

  if (!task) {
    return (
      <div style={{ textAlign: 'center', padding: 48 }}>
        <Spin size="large" />
        <div style={{ marginTop: 16 }}>Loading task...</div>
      </div>
    );
  }

  const getStatusIcon = () => {
    switch (task.status) {
      case 'pending':
      case 'processing':
        return <LoadingOutlined style={{ fontSize: 48, color: '#1890ff' }} spin />;
      case 'completed':
        return <CheckCircleOutlined style={{ fontSize: 48, color: '#52c41a' }} />;
      case 'failed':
        return <CloseCircleOutlined style={{ fontSize: 48, color: '#ff4d4f' }} />;
      default:
        return null;
    }
  };

  const getStatusText = () => {
    switch (task.status) {
      case 'pending':
        return 'Task queued...';
      case 'processing':
        return 'Processing face swap...';
      case 'completed':
        return 'Face swap completed!';
      case 'failed':
        return 'Face swap failed';
      default:
        return 'Unknown status';
    }
  };

  const handleDownload = () => {
    if (task.result_image_url) {
      const url = apiClient.getImageUrl(task.result_image_url);
      const link = document.createElement('a');
      link.href = url;
      link.download = `faceswap_result_${taskId}.jpg`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }
  };

  return (
    <div>
      <Card>
        <div style={{ textAlign: 'center' }}>
          {getStatusIcon()}
          <div style={{ marginTop: 16, fontSize: 18, fontWeight: 500 }}>
            {getStatusText()}
          </div>

          {(task.status === 'pending' || task.status === 'processing') && (
            <div style={{ marginTop: 24, marginBottom: 16 }}>
              <Progress
                percent={task.progress}
                status={task.status === 'processing' ? 'active' : 'normal'}
                strokeColor={{
                  '0%': '#108ee9',
                  '100%': '#87d068',
                }}
              />
            </div>
          )}

          {task.status === 'failed' && task.error_message && (
            <div style={{ marginTop: 16, color: '#ff4d4f' }}>
              Error: {task.error_message}
            </div>
          )}

          {task.processing_time && (
            <div style={{ marginTop: 16, color: '#666', fontSize: 14 }}>
              Processing time: {task.processing_time.toFixed(2)}s
            </div>
          )}
        </div>
      </Card>

      {task.status === 'completed' && task.result_image_url && (
        <Card
          style={{ marginTop: 24 }}
          title="Result"
          extra={
            <Button
              type="primary"
              icon={<DownloadOutlined />}
              onClick={handleDownload}
            >
              Download
            </Button>
          }
        >
          <div style={{ textAlign: 'center' }}>
            <Image
              src={apiClient.getImageUrl(task.result_image_url)}
              alt="Face swap result"
              style={{ maxWidth: '100%', borderRadius: 8 }}
            />
          </div>
        </Card>
      )}
    </div>
  );
};

export default TaskProgress;
