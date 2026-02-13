import React from 'react';
import { Card, Table, Row, Col, ListGroup } from 'react-bootstrap';

interface ResultDisplayProps {
  data: any;
}

// 테이블 형식의 데이터를 보여주는 카드 컴포넌트
const TableDataCard: React.FC<{ title: string; tableData: any[] | null }> = ({ title, tableData }) => {
  if (!tableData || tableData.length === 0) {
    return (
      <Col md={12} className="mb-4">
        <Card bg="dark" text="white">
          <Card.Header as="h5">{title}</Card.Header>
          <Card.Body>
            <Card.Text className="text-white-50">데이터가 없습니다.</Card.Text>
          </Card.Body>
        </Card>
      </Col>
    );
  }

  const headers = Object.keys(tableData[0]);

  return (
    <Col md={12} className="mb-4">
      <Card bg="dark" text="white">
        <Card.Header as="h5">{title}</Card.Header>
        <Card.Body>
          <Table striped bordered hover responsive variant="dark" size="sm">
            <thead>
              <tr>
                {headers.map(header => <th key={header}>{header}</th>)}
              </tr>
            </thead>
            <tbody>
              {tableData.map((row, index) => (
                <tr key={index}>
                  {headers.map(header => <td key={header}>{row[header]}</td>)}
                </tr>
              ))}
            </tbody>
          </Table>
        </Card.Body>
      </Card>
    </Col>
  );
};

// 주요 투자지표를 보여주는 그리드 컴포넌트
const IndicatorGrid: React.FC<{ indicators: any[] | null }> = ({ indicators }) => {
  if (!indicators || indicators.length === 0) {
    return null;
  }
  // Transpose data for better display: {PER: [val1, val2], PBR: [val1, val2]}
  const indicatorMap: { [key: string]: any[] } = {};
  indicators.forEach(row => {
    for (const key in row) {
      if (key !== '구분') {
        if (!indicatorMap[key]) {
          indicatorMap[key] = [];
        }
        indicatorMap[key].push(row[key]);
      }
    }
  });

  return (
    <>
      {Object.entries(indicatorMap).map(([key, values]) => (
        <Col md={6} lg={4} xl={3} className="mb-4" key={key}>
          <Card className="h-100" bg="dark" text="white">
            <Card.Header className="text-center" style={{ fontSize: '1rem' }}>{key}</Card.Header>
            <ListGroup variant="flush">
              {values.map((val, index) => (
                 <ListGroup.Item key={index} className="d-flex justify-content-between align-items-center bg-dark text-white">
                  <span className="text-white-50" style={{fontSize: '0.8rem'}}>{indicators[index]['구분']}</span>
                  <strong style={{fontSize: '1.1rem'}}>{val}</strong>
                </ListGroup.Item>
              ))}
            </ListGroup>
          </Card>
        </Col>
      ))}
    </>
  );
};


const ResultDisplay: React.FC<ResultDisplayProps> = ({ data }) => {
  if (!data) return null;

  return (
    <div>
      <h2 className="text-center mb-4">
        <span className="text-primary">{data.ticker}</span> 분석 결과
      </h2>
      
      <h4 className="mb-3 text-white-50" style={{fontWeight: 300}}>주요 투자지표</h4>
      <Row>
        <IndicatorGrid indicators={data.investment_indicators} />
      </Row>

      <hr className="my-4" />

      <h4 className="mb-3 text-white-50" style={{fontWeight: 300}}>재무제표</h4>
      <Row>
        <TableDataCard title="손익계산서" tableData={data.income_statement} />
        <TableDataCard title="재무상태표" tableData={data.balance_sheet} />
        <TableDataCard title="현금흐름표" tableData={data.cash_flow} />
      </Row>
    </div>
  );
};

export default ResultDisplay;
