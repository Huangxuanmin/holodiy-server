import React from 'react';
import { Card, Row, Col, Button, Typography, Empty, Image, Space, Statistic, Progress } from 'antd';
import { DownloadOutlined, EyeOutlined, CheckCircleOutlined, ClockCircleOutlined } from '@ant-design/icons';

const { Title, Text } = Typography;

const ResultsDisplay = ({ results, onDownloadAll }) => {
  if (results.length === 0) {
    return (
      <div style={{ textAlign: 'center', padding: '100px' }}>
        <Empty
          description={
            <span>
              暂无处理结果
              <br />
              <Text type="secondary">请先上传图像并进行处理</Text>
            </span>
          }
        />
      </div>
    );
  }

  const totalSize = results.reduce((sum, result) => {
    const sizeStr = result.size.replace(' KB', '');
    return sum + parseFloat(sizeStr);
  }, 0);

  const avgSize = totalSize / results.length;

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <Title level={4}>处理结果</Title>
        <Button
          type="primary"
          icon={<DownloadOutlined />}
          onClick={onDownloadAll}
          size="large"
        >
          下载全部 ({results.length}个文件)
        </Button>
      </div>

      <Card style={{ marginBottom: 24 }}>
        <Row gutter={[16, 16]}>
          <Col span={6}>
            <Statistic
              title="生成文件数"
              value={results.length}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Col>
          <Col span={6}>
            <Statistic
              title="总大小"
              value={totalSize.toFixed(1)}
              suffix="KB"
              prefix={<DownloadOutlined />}
            />
          </Col>
          <Col span={6}>
            <Statistic
              title="平均大小"
              value={avgSize.toFixed(1)}
              suffix="KB"
            />
          </Col>
          <Col span={6}>
            <div>
              <Text strong style={{ display: 'block', marginBottom: 8 }}>处理状态</Text>
              <Progress percent={100} status="success" />
              <Text type="secondary" style={{ fontSize: 12 }}>全部完成</Text>
            </div>
          </Col>
        </Row>
      </Card>

      <div className="results-grid">
        {results.map((result, index) => (
          <Card
            key={index}
            className="result-card"
            cover={
              <div style={{ position: 'relative' }}>
                <Image
                  alt={result.name}
                  src={result.preview_url}
                  style={{ height: 150, objectFit: 'cover' }}
                  preview={{
                    mask: <EyeOutlined />,
                  }}
                />
                <div className="status-badge">
                  <CheckCircleOutlined style={{ color: '#52c41a', fontSize: 16 }} />
                </div>
              </div>
            }
            actions={[
              <Button
                type="link"
                icon={<DownloadOutlined />}
                href={result.download_url}
                target="_blank"
              >
                下载
              </Button>,
              <Button
                type="link"
                icon={<EyeOutlined />}
                onClick={() => window.open(result.preview_url, '_blank')}
              >
                预览
              </Button>
            ]}
          >
            <Card.Meta
              title={result.name}
              description={
                <Space direction="vertical" size="small">
                  <Text type="secondary">{result.size}</Text>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    Hogel #{index + 1}
                  </Text>
                </Space>
              }
            />
          </Card>
        ))}
      </div>

      <Card style={{ marginTop: 24 }}>
        <Title level={5}>使用说明</Title>
        <Row gutter={[16, 16]}>
          <Col span={8}>
            <div style={{ textAlign: 'center' }}>
              <EyeOutlined style={{ fontSize: 24, color: '#1890ff', marginBottom: 8 }} />
              <Text strong style={{ display: 'block' }}>预览图像</Text>
              <Text type="secondary">点击图像可放大预览</Text>
            </div>
          </Col>
          <Col span={8}>
            <div style={{ textAlign: 'center' }}>
              <DownloadOutlined style={{ fontSize: 24, color: '#52c41a', marginBottom: 8 }} />
              <Text strong style={{ display: 'block' }}>下载单个</Text>
              <Text type="secondary">点击下载按钮下载单个文件</Text>
            </div>
          </Col>
          <Col span={8}>
            <div style={{ textAlign: 'center' }}>
              <DownloadOutlined style={{ fontSize: 24, color: '#722ed1', marginBottom: 8 }} />
              <Text strong style={{ display: 'block' }}>批量下载</Text>
              <Text type="secondary">点击顶部按钮下载全部文件</Text>
            </div>
          </Col>
        </Row>
      </Card>
    </div>
  );
};

export default ResultsDisplay;