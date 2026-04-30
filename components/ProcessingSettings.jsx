import React, { useState, useEffect } from 'react';
import { Card, Form, InputNumber, Slider, Select, Switch, Button, Row, Col, Typography, Divider, Tabs, Space } from 'antd';
import { PlayCircleOutlined, SettingOutlined } from '@ant-design/icons';

const { Title, Text } = Typography;
const { TabPane } = Tabs;
const { Option } = Select;

const ProcessingSettings = ({ settings, onChange, onProcessHorizontal, onProcessFull }) => {
  const [form] = Form.useForm();
  const [activeTab, setActiveTab] = useState('horizontal');

  // 初始化表单值
  useEffect(() => {
    if (settings) {
      form.setFieldsValue({
        horizontal: settings.horizontal || {},
        full: settings.full || {},
      });
    }
  }, [settings, form]);

  const handleValuesChange = (changedValues, allValues) => {
    onChange(allValues);
  };

  const handleProcess = () => {
    if (activeTab === 'horizontal') {
      onProcessHorizontal();
    } else {
      onProcessFull();
    }
  };

  const horizontalSettings = (
    <Form.Item name="horizontal" noStyle>
      <Card title="水平视差设置" className="settings-card">
        <Row gutter={[16, 16]}>
          <Col span={12}>
            <Form.Item
              name={['horizontal', 'hogelCount']}
              label="Hogel数量 (C)"
              rules={[{ required: true, message: '请输入Hogel数量' }]}
            >
              <InputNumber
                min={1}
                max={100}
                style={{ width: '100%' }}
                placeholder="每张图像分割的份数"
              />
            </Form.Item>
            <Text type="secondary">每张图像将被水平分割成C份</Text>
          </Col>
          
          <Col span={12}>
            <Form.Item
              name={['horizontal', 'hogelWidth']}
              label="Hogel宽度 (像素)"
              rules={[{ required: true, message: '请输入Hogel宽度' }]}
            >
              <InputNumber
                min={100}
                max={2000}
                style={{ width: '100%' }}
                placeholder="输出Hogel图像的宽度"
              />
            </Form.Item>
            <Text type="secondary">每个Hogel图像的固定像素宽度</Text>
          </Col>
        </Row>

        <Row gutter={[16, 16]}>
          <Col span={12}>
            <Form.Item
              name={['horizontal', 'heightMode']}
              label="高度模式"
              initialValue="fixed"
            >
              <Select style={{ width: '100%' }}>
                <Option value="fixed">固定高度</Option>
                <Option value="original">保持原始高度</Option>
              </Select>
            </Form.Item>
          </Col>
          
          <Col span={12}>
            <Form.Item
              noStyle
              shouldUpdate={(prevValues, currentValues) => 
                prevValues.horizontal?.heightMode !== currentValues.horizontal?.heightMode
              }
            >
              {({ getFieldValue }) => {
                const heightMode = getFieldValue(['horizontal', 'heightMode']);
                if (heightMode === 'fixed') {
                  return (
                    <Form.Item
                      name={['horizontal', 'hogelHeight']}
                      label="Hogel高度 (像素)"
                      rules={[{ required: true, message: '请输入Hogel高度' }]}
                    >
                      <InputNumber
                        min={100}
                        max={2000}
                        style={{ width: '100%' }}
                        placeholder="输出Hogel图像的高度"
                      />
                    </Form.Item>
                  );
                }
                return null;
              }}
            </Form.Item>
          </Col>
        </Row>

        <Row gutter={[16, 16]}>
          <Col span={12}>
            <Form.Item
              name={['horizontal', 'quality']}
              label="输出质量"
            >
              <Slider
                min={1}
                max={100}
                marks={{
                  1: '1',
                  25: '25',
                  50: '50',
                  75: '75',
                  100: '100'
                }}
              />
            </Form.Item>
            <Text type="secondary">JPEG压缩质量 (1-100)</Text>
          </Col>
          
          <Col span={12}>
            <Form.Item
              name={['horizontal', 'enableAntiAliasing']}
              label="抗锯齿"
              valuePropName="checked"
              initialValue={true}
            >
              <Switch />
            </Form.Item>
            <Text type="secondary">启用图像抗锯齿处理</Text>
            
            <Form.Item
              name={['horizontal', 'enableOptimization']}
              label="优化处理"
              valuePropName="checked"
              initialValue={true}
            >
              <Switch />
            </Form.Item>
            <Text type="secondary">启用图像优化处理</Text>
          </Col>
        </Row>
      </Card>
    </Form.Item>
  );

  const fullParallaxSettings = (
    <Form.Item name="full" noStyle>
      <Card title="全视差设置" className="settings-card">
        <Row gutter={[16, 16]}>
          <Col span={8}>
            <Form.Item
              name={['full', 'canvasWidth']}
              label="画幅宽度 (mm)"
              rules={[{ required: true, message: '请输入画幅宽度' }]}
            >
              <InputNumber
                min={1}
                max={1000}
                step={0.1}
                style={{ width: '100%' }}
                placeholder="画幅物理宽度"
              />
            </Form.Item>
            <Text type="secondary">全息图的物理宽度</Text>
          </Col>
          
          <Col span={8}>
            <Form.Item
              name={['full', 'canvasHeight']}
              label="画幅高度 (mm)"
              rules={[{ required: true, message: '请输入画幅高度' }]}
            >
              <InputNumber
                min={1}
                max={1000}
                step={0.1}
                style={{ width: '100%' }}
                placeholder="画幅物理高度"
              />
            </Form.Item>
            <Text type="secondary">全息图的物理高度</Text>
          </Col>
          
          <Col span={8}>
            <Form.Item
              name={['full', 'exposureWidth']}
              label="曝光宽度 (mm)"
              rules={[{ required: true, message: '请输入曝光宽度' }]}
            >
              <InputNumber
                min={0.1}
                max={100}
                step={0.1}
                style={{ width: '100%' }}
                placeholder="单次曝光宽度"
              />
            </Form.Item>
            <Text type="secondary">单次曝光的物理宽度</Text>
          </Col>
        </Row>

        <Row gutter={[16, 16]}>
          <Col span={12}>
            <Form.Item
              name={['full', 'quality']}
              label="输出质量"
            >
              <Slider
                min={1}
                max={100}
                marks={{
                  1: '1',
                  25: '25',
                  50: '50',
                  75: '75',
                  100: '100'
                }}
              />
            </Form.Item>
            <Text type="secondary">JPEG压缩质量 (1-100)</Text>
          </Col>
          
          <Col span={12}>
            <div style={{ paddingTop: 30 }}>
              <Text strong>计算参数:</Text>
              <div style={{ marginTop: 8 }}>
                <Form.Item noStyle shouldUpdate>
                  {({ getFieldValue }) => {
                    const canvasWidth = getFieldValue(['full', 'canvasWidth']) || 100;
                    const exposureWidth = getFieldValue(['full', 'exposureWidth']) || 10;
                    const C = Math.floor(canvasWidth / exposureWidth);
                    
                    return (
                      <Space direction="vertical" size="small">
                        <Text type="secondary">分割份数 C: {C}</Text>
                        <Text type="secondary">每张图像将被分割成 {C}×{C} 个小方块</Text>
                        <Text type="secondary">总小方块数: {C * C}</Text>
                      </Space>
                    );
                  }}
                </Form.Item>
              </div>
            </div>
          </Col>
        </Row>
      </Card>
    </Form.Item>
  );

  return (
    <div>
      <Title level={4}>处理设置</Title>
      
      <Form
        form={form}
        layout="vertical"
        onValuesChange={handleValuesChange}
      >
        <Tabs activeKey={activeTab} onChange={setActiveTab}>
          <TabPane tab="水平视差" key="horizontal">
            {horizontalSettings}
          </TabPane>
          <TabPane tab="全视差" key="full">
            {fullParallaxSettings}
          </TabPane>
        </Tabs>

        <Divider />
        
        <div style={{ textAlign: 'center' }}>
          <Button
            type="primary"
            size="large"
            icon={<PlayCircleOutlined />}
            onClick={handleProcess}
            className="process-button"
          >
            {activeTab === 'horizontal' ? '生成水平视差Hogel' : '生成全视差Hogel'}
          </Button>
          
          <div style={{ marginTop: 16 }}>
            <Text type="secondary">
              {activeTab === 'horizontal' 
                ? '将根据水平视差设置处理上传的图像' 
                : '将根据全视差设置处理上传的图像'}
            </Text>
          </div>
        </div>
      </Form>
    </div>
  );
};

export default ProcessingSettings;