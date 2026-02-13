import { useState } from 'react';
import { Container, Row, Col, Spinner, Alert } from 'react-bootstrap';
import TickerForm from './components/TickerForm'; 
import ResultDisplay from './components/ResultDisplay';
import { scrapeTickerData } from './services/api';

function App() {
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(false);

  const handleScrape = async (ticker: string) => {
    setLoading(true);
    setData(null);
    setError(null);
    try {
      const response = await scrapeTickerData(ticker);
      setData(response);
    } catch (err: any) {
      setError(err.message || '알 수 없는 오류가 발생했습니다.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Container className="py-4">
      <Row className="justify-content-center text-center mb-4">
        <Col md={10}>
          <h1 className="display-5 mb-3" style={{ fontWeight: 300 }}>
            주식 정보 <span style={{ fontWeight: 600 }}>스크레이퍼</span>
          </h1>
          <p className="lead text-white-50">
            조회할 종목의 코드(예: 005930, AAPL)를 입력하세요.
          </p>
        </Col>
      </Row>
      
      <Row className="justify-content-center">
        <Col md={8} lg={6}>
          <TickerForm onScrape={handleScrape} loading={loading} />
        </Col>
      </Row>

      <Row className="justify-content-center mt-4">
        <Col md={11}>
          {loading && (
            <div className="text-center">
              <Spinner animation="border" variant="primary" />
              <p className="mt-2 text-white-50">데이터를 가져오는 중...</p>
            </div>
          )}
          {error && <Alert variant="danger">{error}</Alert>}
          {data && <ResultDisplay data={data} />}
        </Col>
      </Row>
    </Container>
  );
}

export default App;