import React, { useState, useEffect } from 'react';
import { Layout, Menu, Typography, Card, Row, Col, message, Spin } from 'antd';
import { UploadOutlined, SettingOutlined, FileImageOutlined, DownloadOutlined } from '@ant-design/icons';
import './App.css';
import FileUpload from './components/FileUpload.jsx';
import ProcessingSettings from './components/ProcessingSettings.jsx';
import ResultsDisplay from './components/ResultsDisplay.jsx';

const { Header, Content, Sider } = Layout;
const { Title } = Typography;

function App() {
  const [selectedMenu, setSelectedMenu] = useState('upload');
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const [processingSettings, setProcessingSettings] = useState({});
  const [processingResults, setProcessingResults] = useState([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [apiStatus, setApiStatus] = useState('checking');

  // 检查API健康状态
  useEffect(() => {
    const checkApiHealth = async () => {
      try {
        const response = await fetch('/api/health');
        if (response.ok) {
          setApiStatus('healthy');
        } else {
          setApiStatus('unhealthy');
        }
      } catch (error) {
        setApiStatus('unhealthy');
        console.error('API健康检查失败:', error);
      }
    };

    checkApiHealth();
    const interval = setInterval(checkApiHealth, 30000); // 每30秒检查一次
    return () => clearInterval(interval);
  }, []);

  // 获取默认设置
  useEffect(() => {
    const fetchDefaultSettings = async () => {
      try {
        const response = await fetch('/api/settings');
        if (response.ok) {
          const data = await response.json();
          if (data.success) {
            setProcessingSettings(data.settings);
          }
        }
      } catch (error) {
        console.error('获取默认设置失败:', error);
      }
    };

    fetchDefaultSettings();
  }, []);

  const handleFileUpload = (files) => {
    setUploadedFiles(files);
    message.success(`成功上传 ${files.length} 个文件`);
  };

  const handleSettingsChange = (settings) => {
    setProcessingSettings(settings);
  };

  const handleProcess = async (processorType) => {
    if (uploadedFiles.length === 0) {
      message.warning('请先上传图像文件');
      return;
    }

    setIsProcessing(true);
    try {
      const formData = new FormData();
      uploadedFiles.forEach(file => {
        formData.append('files', file);
      });

      // 根据处理器类型添加不同的参数
      if (processorType === 'horizontal') {
        const settings = processingSettings.horizontal || {};
        formData.append('C', settings.hogelCount || 10);
        formData.append('width', settings.hogelWidth || 500);
        if (settings.heightMode === 'fixed' && settings.hogelHeight) {
          formData.append('height', settings.hogelHeight);
        }
        formData.append('quality', settings.quality || 95);
      } else if (processorType === 'full') {
        const settings = processingSettings.full || {};
        formData.append('canvas_width', settings.canvasWidth || 100.0);
        formData.append('canvas_height', settings.canvasHeight || 100.0);
        formData.append('exposure_width', settings.exposureWidth || 10.0);
        formData.append('quality', settings.quality || 95);
      }

      const endpoint = processorType === 'horizontal' 
        ? '/api/generate-hogel' 
        : '/api/generate-full-parallax-hogel';

      const response = await fetch(endpoint, {
        method: 'POST',
        body: formData,
      });

      const data = await response.json();
      
      if (data.success) {
        setProcessingResults(data.hogels);
        message.success(data.message);
      } else {
        message.error(data.error || '处理失败');
      }
    } catch (error) {
      console.error('处理失败:', error);
      message.error('处理失败，请检查网络连接');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleDownloadAll = async () => {
    try {
      const response = await fetch('/api/download-all');
      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'hogel_images.zip';
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        message.success('下载成功');
      } else {
        message.error('下载失败');
      }
    } catch (error) {
      console.error('下载失败:', error);
      message.error('下载失败');
    }
  };

  const renderContent = () => {
    if (isProcessing) {
      return (
        <div style={{ textAlign: 'center', padding: '100px' }}>
          <Spin size="large" />
          <div style={{ marginTop: 20 }}>正在处理图像，请稍候...</div>
        </div>
      );
    }

    switch (selectedMenu) {
      case 'upload':
        return <FileUpload onUpload={handleFileUpload} uploadedFiles={uploadedFiles} />;
      case 'settings':
        return (
          <ProcessingSettings 
            settings={processingSettings} 
            onChange={handleSettingsChange}
            onProcessHorizontal={() => handleProcess('horizontal')}
            onProcessFull={() => handleProcess('full')}
          />
        );
      case 'results':
        return (
          <ResultsDisplay 
            results={processingResults}
            onDownloadAll={handleDownloadAll}
          />
        );
      default:
        return <FileUpload onUpload={handleFileUpload} uploadedFiles={uploadedFiles} />;
    }
  };

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header style={{ background: '#001529', padding: '0 20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', height: '100%' }}>
          <Title level={3} style={{ color: 'white', margin: 0 }}>
            Hogel图像处理系统
          </Title>
          <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center' }}>
            <div style={{ 
              width: 10, 
              height: 10, 
              borderRadius: '50%', 
              backgroundColor: apiStatus === 'healthy' ? '#52c41a' : '#f5222d',
              marginRight: 8 
            }} />
            <span style={{ color: 'white' }}>
              {apiStatus === 'healthy' ? 'API正常' : 'API异常'}
            </span>
          </div>
        </div>
      </Header>
      <Layout>
        <Sider width={200} style={{ background: '#fff' }}>
          <Menu
            mode="inline"
            selectedKeys={[selectedMenu]}
            style={{ height: '100%', borderRight: 0 }}
            onSelect={({ key }) => setSelectedMenu(key)}
          >
            <Menu.Item key="upload" icon={<UploadOutlined />}>
              文件上传
            </Menu.Item>
            <Menu.Item key="settings" icon={<SettingOutlined />}>
              处理设置
            </Menu.Item>
            <Menu.Item key="results" icon={<FileImageOutlined />}>
              处理结果
            </Menu.Item>
            {processingResults.length > 0 && (
              <Menu.Item 
                key="download" 
                icon={<DownloadOutlined />}
                onClick={handleDownloadAll}
              >
                下载全部
              </Menu.Item>
            )}
          </Menu>
        </Sider>
        <Layout style={{ padding: '24px' }}>
          <Content style={{ background: '#fff', padding: 24, margin: 0, minHeight: 280 }}>
            {renderContent()}
          </Content>
        </Layout>
      </Layout>
    </Layout>
  );
}

export default App;