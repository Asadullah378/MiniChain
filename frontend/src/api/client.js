import axios from "axios";
import { mockStatus, mockBlocks, mockMempool } from "./mockData";

const API_BASE_URL = import.meta.env.VITE_API_URL || window.location.origin;

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

export const setApiBaseUrl = (url) => {
  api.defaults.baseURL = url;
};

export const getStatus = async () => {
  try {
    const response = await api.get("/status");
    return response.data;
  } catch (error) {
    console.warn("API Error (getStatus), using fallback:", error.message);
    return mockStatus;
  }
};

export const getBlocks = async (start = 0, limit = 10) => {
  try {
    const response = await api.get("/blocks", {
      params: { start, limit },
    });
    return response.data;
  } catch (error) {
    console.warn("API Error (getBlocks), using fallback:", error.message);
    return mockBlocks;
  }
};

export const getBlockDetails = async (height) => {
  const response = await api.get(`/blocks/${height}`);
  return response.data;
};

export const getMempool = async () => {
  try {
    const response = await api.get("/mempool");
    return response.data;
  } catch (error) {
    console.warn("API Error (getMempool), using fallback:", error.message);
    return mockMempool;
  }
};

export const submitTransaction = async (transaction) => {
  const response = await api.post("/submit", transaction);
  return response.data;
};

export default api;
