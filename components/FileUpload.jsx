import React, { useState } from 'react';
import { Upload, Button, List, Card, Typography, Space, Image, Progress } from 'antd';
import { UploadOutlined, DeleteOutlined, EyeOutlined, FileImageOutlined } from '@ant-design/icons';

const { Title, Text } = Typography;

const FileUpload = ({ onUpload, uploadedFiles }) => {
  const [fileList, setFileList] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState({});

  const handleUpload = async () => {
    if (fileList.length === 0) {
      return;
    }

    setUploading(true);
    const formData = new FormData();
    
    fileList.forEach(file => {
      formData.append('files', file);
    });

    try {
      const response = await fetch('/api/upload', {
        method: 'POST',
        body: formData,
      });

      const data = await response.json();
      
      if (data.success) {
        // 将上传的文件传递给父组件
        const files = fileList.map(file => file.originFileObj || file);
        onUpload(files);
        setFileList([]);
        setUploadProgress({});
      } else {
        console.error('上传失败:', data.error);
      }
    } catch (error) {
      console.error('上传失败:', error);
    } finally {
      setUploading(false);
    }
  };

  const uploadProps = {
    onRemove: (file) => {
      const index = fileList.indexOf(file);
      const newFileList = fileList.slice();
      newFileList.splice(index, 1);
      setFileList(newFileList);
    },
    beforeUpload: (file) => {
      // 检查文件类型
      const isImage = file.type.startsWith('image/');
      if (!isImage) {
        console.error('只能上传图像文件');
        return false;
      }

      // 检查文件大小（最大10MB）
      const isLt10M = file.size / 1024 / 1024 < 10;
      if (!isLt10M) {
        console.error('文件大小不能超过10MB');
        return false;
      }

      setFileList([...fileList, file]);
      return false; // 手动上传
    },
    fileList,
    multiple: true,
    accept: 'image/*',
    showUploadList: false,
  };

  const totalSize = fileList.reduce((sum, file) => sum + (file.size || 0), 0);
  const totalSizeMB = (totalSize / 1024 / 1024).toFixed(2);

  return (
    <div>
      <Title level={4}>上传图像文件</Title>
      <Card>
        <div className="upload-area">
          <Upload.Dragger {...uploadProps}>
            <p className="ant-upload-drag-icon">
              <UploadOutlined style={{ fontSize: 48, color: '#1890ff' }} />
            </p>
            <p className="ant-upload-text">点击或拖拽文件到此区域上传</p>
            <p className="ant-upload-hint">
              支持单个或批量上传，支持JPG、PNG、BMP格式，单个文件不超过10MB
            </p>
          </Upload.Dragger>
          
          {fileList.length > 0 && (
            <div style={{ marginTop: 20 }}>
              <Space direction="vertical" style={{ width: '100%' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Text>已选择 {fileList.length} 个文件，总计 {totalSizeMB} MB</Text>
                  <Button
                    type="primary"
                    onClick={handleUpload}
                    loading={uploading}
                    icon={<UploadOutlined />}
                  >
                    {uploading ? '上传中...' : '开始上传'}
                  </Button>
                </div>
                
                <List
                  size="small"
                  dataSource={fileList}
                  renderItem={(file, index) => (
                    <List.Item
                      actions={[
                        <Button
                          type="text"
                          icon={<DeleteOutlined />}
                          onClick={() => uploadProps.onRemove(file)}
                        />
                      ]}
                    >
                      <List.Item.Meta
                        avatar={
                          file.type?.startsWith('image/') ? (
                            <Image
                              width={40}
                              height={40}
                              src={URL.createObjectURL(file)}
                              preview={{
                                mask: <EyeOutlined />,
                              }}
                            />
                          ) : (
                            <div style={{ width: 40, height: 40, background: '#f0f0f0', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                              <FileImageOutlined />
                            </div>
                          )
                        }
                        title={file.name}
                        description={`${(file.size / 1024 / 1024).toFixed(2)} MB`}
                      />
                      {uploadProgress[file.uid] && (
                        <Progress
                          percent={uploadProgress[file.uid]}
                          size="small"
                          style={{ width: 100 }}
                        />
                      )}
                    </List.Item>
                  )}
                />
              </Space>
            </div>
          )}
        </div>
      </Card>

      {uploadedFiles.length > 0 && (
        <Card style={{ marginTop: 20 }}>
          <Title level={5}>已上传的文件</Title>
          <List
            grid={{ gutter: 16, column: 4 }}
            dataSource={uploadedFiles}
            renderItem={(file, index) => (
              <List.Item>
                <Card
                  cover={
                    <img
                      alt={file.name}
                      src={URL.createObjectURL(file)}
                      style={{ height: 120, objectFit: 'cover' }}
                    />
                  }
                  actions={[
                    <Button
                      type="text"
                      icon={<DeleteOutlined />}
                      onClick={() => {
                        const newFiles = [...uploadedFiles];
                        newFiles.splice(index, 1);
                        onUpload(newFiles);
                      }}
                    />
                  ]}
                >
                  <Card.Meta
                    title={file.name}
                    description={`${(file.size / 1024 / 1024).toFixed(2)} MB`}
                  />
                </Card>
              </List.Item>
            )}
          />
        </Card>
      )}
    </div>
  );
};

export default FileUpload;