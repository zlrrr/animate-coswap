/**
 * Template Gallery Component
 *
 * Displays available couple templates for selection
 */

import React, { useEffect, useState } from 'react';
import { Card, Row, Col, Spin, Tag, Empty, message, Radio } from 'antd';
import type { RadioChangeEvent } from 'antd';
import { CheckCircleOutlined } from '@ant-design/icons';
import { apiClient, Template } from '../services/api';

const { Meta } = Card;

interface TemplateGalleryProps {
  onSelect: (templateId: number) => void;
  selectedId?: number;
}

export const TemplateGallery: React.FC<TemplateGalleryProps> = ({
  onSelect,
  selectedId,
}) => {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedCategory, setSelectedCategory] = useState<string>('all');

  useEffect(() => {
    fetchTemplates();
  }, [selectedCategory]);

  const fetchTemplates = async () => {
    setLoading(true);
    try {
      const data = await apiClient.getTemplates(selectedCategory, 20, 0);
      setTemplates(data);
    } catch (error: any) {
      message.error(`Failed to load templates: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleCategoryChange = (e: RadioChangeEvent) => {
    setSelectedCategory(e.target.value);
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: 48 }}>
        <Spin size="large" />
        <div style={{ marginTop: 16 }}>Loading templates...</div>
      </div>
    );
  }

  if (templates.length === 0) {
    return (
      <Empty
        description="No templates available"
        style={{ padding: 48 }}
      />
    );
  }

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <div style={{ marginBottom: 12, fontWeight: 500 }}>Category:</div>
        <Radio.Group value={selectedCategory} onChange={handleCategoryChange}>
          <Radio.Button value="all">All</Radio.Button>
          <Radio.Button value="acg">ACG/Anime</Radio.Button>
          <Radio.Button value="movie">Movies</Radio.Button>
          <Radio.Button value="tv">TV Shows</Radio.Button>
          <Radio.Button value="custom">Custom</Radio.Button>
        </Radio.Group>
      </div>

      <Row gutter={[16, 16]}>
        {templates.map((template) => (
          <Col key={template.id} xs={24} sm={12} md={8} lg={6}>
            <Card
              hoverable
              cover={
                <div style={{ position: 'relative', height: 200, overflow: 'hidden' }}>
                  <img
                    alt={template.name}
                    src={apiClient.getImageUrl(template.image_url)}
                    style={{
                      width: '100%',
                      height: '100%',
                      objectFit: 'cover',
                    }}
                  />
                  {selectedId === template.id && (
                    <div
                      style={{
                        position: 'absolute',
                        top: 0,
                        left: 0,
                        right: 0,
                        bottom: 0,
                        backgroundColor: 'rgba(24, 144, 255, 0.2)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                      }}
                    >
                      <CheckCircleOutlined
                        style={{ fontSize: 48, color: '#1890ff' }}
                      />
                    </div>
                  )}
                </div>
              }
              onClick={() => onSelect(template.id)}
              style={{
                border: selectedId === template.id ? '2px solid #1890ff' : undefined,
              }}
            >
              <Meta
                title={template.name}
                description={
                  <div>
                    <Tag color="blue">{template.category}</Tag>
                    <Tag>{template.face_count} faces</Tag>
                    {template.is_preprocessed && (
                      <Tag color="green">Preprocessed</Tag>
                    )}
                  </div>
                }
              />
            </Card>
          </Col>
        ))}
      </Row>
    </div>
  );
};

export default TemplateGallery;
