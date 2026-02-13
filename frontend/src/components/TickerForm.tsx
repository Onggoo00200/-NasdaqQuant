import React, { useState } from 'react';
import { Form, Button, FloatingLabel, Row, Col } from 'react-bootstrap';

interface TickerFormProps {
  onScrape: (ticker: string) => void;
  loading: boolean;
}

const TickerForm: React.FC<TickerFormProps> = ({ onScrape, loading }) => {
  const [ticker, setTicker] = useState<string>('005930'); // 삼성전자를 기본값으로

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (ticker.trim()) {
      onScrape(ticker.trim().toUpperCase());
    }
  };

  return (
    <Form onSubmit={handleSubmit}>
      <Row className="align-items-center">
        <Col>
          <FloatingLabel controlId="floatingTicker" label="종목 코드 (예: 005930, AAPL)">
            <Form.Control
              type="text"
              value={ticker}
              onChange={(e) => setTicker(e.target.value)}
              placeholder="종목 코드 (예: 005930, AAPL)"
              disabled={loading}
              required
            />
          </FloatingLabel>
        </Col>
        <Col xs="auto">
          <Button
            variant="primary"
            type="submit"
            disabled={loading}
            style={{ height: '58px', width: '100px' }}
          >
            {loading ? '조회중...' : '조회'}
          </Button>
        </Col>
      </Row>
    </Form>
  );
};

export default TickerForm;
