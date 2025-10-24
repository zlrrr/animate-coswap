/**
 * Main Application Component
 */

import React from 'react';
import { Layout, Menu } from 'antd';
import { HomeOutlined, ApiOutlined } from '@ant-design/icons';
import FaceSwapWorkflow from './pages/FaceSwapWorkflow';
import './App.css';

const { Header, Content, Footer } = Layout;

function App() {
  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header style={{ display: 'flex', alignItems: 'center' }}>
        <div
          style={{
            color: 'white',
            fontSize: 20,
            fontWeight: 'bold',
            marginRight: 48,
          }}
        >
          Couple Face-Swap
        </div>
        <Menu
          theme="dark"
          mode="horizontal"
          defaultSelectedKeys={['home']}
          style={{ flex: 1, minWidth: 0 }}
          items={[
            {
              key: 'home',
              icon: <HomeOutlined />,
              label: 'Home',
            },
            {
              key: 'api',
              icon: <ApiOutlined />,
              label: 'API Docs',
              onClick: () => window.open('http://localhost:8000/docs', '_blank'),
            },
          ]}
        />
      </Header>

      <Content style={{ padding: '24px 48px', background: '#f0f2f5' }}>
        <FaceSwapWorkflow />
      </Content>

      <Footer style={{ textAlign: 'center' }}>
        Couple Face-Swap ©{new Date().getFullYear()} | AI-Powered Face Swapping
      </Footer>
    </Layout>
  );
}

export default App;
