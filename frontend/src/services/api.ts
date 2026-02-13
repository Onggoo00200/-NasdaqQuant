import axios from 'axios';

const API_BASE_URL = 'http://127.0.0.1:8000/api'; // 백엔드 FastAPI URL

export const scrapeTickerData = async (ticker: string) => {
  try {
    const response = await axios.get(`${API_BASE_URL}/scrape`, {
      params: { ticker: ticker },
    });
    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error) && error.response) {
      // 백엔드가 2xx 범위를 벗어나는 상태 코드로 응답했을 때
      throw new Error(error.response.data.detail || '데이터를 가져오는 중 에러가 발생했습니다.');
    } else if (axios.isAxiosError(error) && error.request) {
      // 요청은 완료되었지만 응답을 받지 못했을 때
      throw new Error('서버에서 응답이 없습니다. 백엔드 서버가 실행 중인지 확인해주세요.');
    } else {
      // 요청 설정 중에 문제가 발생했을 때
      throw new Error('요청을 보내는 중 오류가 발생했습니다: ' + (error as Error).message);
    }
  }
};
