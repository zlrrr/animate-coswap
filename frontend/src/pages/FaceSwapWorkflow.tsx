/**
 * Face Swap Workflow Page
 *
 * Main workflow for uploading photos, selecting template, and creating face swap
 */

import React, { useState } from 'react';
import { Steps, Button, message, Card } from 'antd';
import ImageUploader from '../components/ImageUploader';
import TemplateGallery from '../components/TemplateGallery';
import TaskProgress from '../components/TaskProgress';
import { apiClient, ImageUploadResponse } from '../services/api';

const { Step } = Steps;

export const FaceSwapWorkflow: React.FC = () => {
  const [currentStep, setCurrentStep] = useState(0);
  const [husbandImageId, setHusbandImageId] = useState<number | null>(null);
  const [wifeImageId, setWifeImageId] = useState<number | null>(null);
  const [templateId, setTemplateId] = useState<number | null>(null);
  const [taskId, setTaskId] = useState<number | null>(null);
  const [processing, setProcessing] = useState(false);

  const handleHusbandUpload = (imageData: ImageUploadResponse) => {
    setHusbandImageId(imageData.image_id);
  };

  const handleWifeUpload = (imageData: ImageUploadResponse) => {
    setWifeImageId(imageData.image_id);
  };

  const handleTemplateSelect = (id: number) => {
    setTemplateId(id);
  };

  const startProcessing = async () => {
    if (!husbandImageId || !wifeImageId || !templateId) {
      message.error('Please complete all steps first!');
      return;
    }

    setProcessing(true);

    try {
      const response = await apiClient.createFaceSwapTask({
        husband_image_id: husbandImageId,
        wife_image_id: wifeImageId,
        template_id: templateId,
      });

      setTaskId(response.task_id);
      setCurrentStep(3);
      message.success('Face swap task created! Processing...');
    } catch (error: any) {
      message.error(`Failed to create task: ${error.response?.data?.detail || error.message}`);
    } finally {
      setProcessing(false);
    }
  };

  const resetWorkflow = () => {
    setCurrentStep(0);
    setHusbandImageId(null);
    setWifeImageId(null);
    setTemplateId(null);
    setTaskId(null);
  };

  const steps = [
    {
      title: 'Upload Photos',
      description: 'Husband & Wife',
    },
    {
      title: 'Select Template',
      description: 'Choose style',
    },
    {
      title: 'Process',
      description: 'Face swap',
    },
    {
      title: 'Result',
      description: 'Download',
    },
  ];

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto', padding: 24 }}>
      <Card>
        <h1 style={{ textAlign: 'center', marginBottom: 32 }}>
          Couple Face-Swap
        </h1>

        <Steps current={currentStep} style={{ marginBottom: 32 }}>
          {steps.map((step) => (
            <Step key={step.title} title={step.title} description={step.description} />
          ))}
        </Steps>

        <div style={{ minHeight: 400 }}>
          {currentStep === 0 && (
            <div>
              <Card title="Step 1: Upload Photos" style={{ marginBottom: 24 }}>
                <p style={{ marginBottom: 24, color: '#666' }}>
                  Upload clear photos of both people. Make sure faces are visible and well-lit.
                </p>

                <ImageUploader
                  imageType="husband"
                  label="Upload Husband's Photo"
                  onUploadComplete={handleHusbandUpload}
                />

                <ImageUploader
                  imageType="wife"
                  label="Upload Wife's Photo"
                  onUploadComplete={handleWifeUpload}
                />

                <Button
                  type="primary"
                  size="large"
                  onClick={() => setCurrentStep(1)}
                  disabled={!husbandImageId || !wifeImageId}
                  style={{ marginTop: 24 }}
                >
                  Next: Select Template
                </Button>
              </Card>
            </div>
          )}

          {currentStep === 1 && (
            <div>
              <Card title="Step 2: Choose a Template">
                <p style={{ marginBottom: 24, color: '#666' }}>
                  Select a couple template that you'd like to use. Your faces will be swapped into this image.
                </p>

                <TemplateGallery
                  onSelect={handleTemplateSelect}
                  selectedId={templateId || undefined}
                />

                <div style={{ marginTop: 24, display: 'flex', gap: 16 }}>
                  <Button size="large" onClick={() => setCurrentStep(0)}>
                    Back
                  </Button>
                  <Button
                    type="primary"
                    size="large"
                    onClick={() => setCurrentStep(2)}
                    disabled={!templateId}
                  >
                    Next: Start Processing
                  </Button>
                </div>
              </Card>
            </div>
          )}

          {currentStep === 2 && (
            <div>
              <Card title="Step 3: Ready to Process">
                <div style={{ textAlign: 'center', padding: 48 }}>
                  <h3>Everything is ready!</h3>
                  <p style={{ fontSize: 16, color: '#666', margin: '24px 0' }}>
                    Click the button below to start the face-swap process.
                    This usually takes 5-10 seconds.
                  </p>

                  <div style={{ marginTop: 32, display: 'flex', gap: 16, justifyContent: 'center' }}>
                    <Button size="large" onClick={() => setCurrentStep(1)}>
                      Back
                    </Button>
                    <Button
                      type="primary"
                      size="large"
                      loading={processing}
                      onClick={startProcessing}
                    >
                      {processing ? 'Starting...' : 'Start Face Swap'}
                    </Button>
                  </div>
                </div>
              </Card>
            </div>
          )}

          {currentStep === 3 && taskId && (
            <div>
              <Card title="Step 4: Processing & Result">
                <TaskProgress
                  taskId={taskId}
                  onComplete={() => {
                    message.success('Face swap completed successfully!');
                  }}
                  onError={(error) => {
                    message.error(`Face swap failed: ${error}`);
                  }}
                />

                <div style={{ marginTop: 24, textAlign: 'center' }}>
                  <Button size="large" onClick={resetWorkflow}>
                    Create Another
                  </Button>
                </div>
              </Card>
            </div>
          )}
        </div>
      </Card>
    </div>
  );
};

export default FaceSwapWorkflow;
