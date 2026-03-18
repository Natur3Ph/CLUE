// src/api/benchmark.js
import request from './request'

// 获取数据集列表
export function fetchDatasets() {
  return request.get('/api/datasets')
}

// 启动 Benchmark
export function runBenchmark(data) {
  return request.post('/api/benchmarks/run', data)
}

// 获取 Benchmark 运行记录列表
export function fetchBenchmarkRuns() {
  return request.get('/api/benchmarks/runs')
}

// 获取某次 Benchmark 详情
export function fetchBenchmarkRunDetail(runId) {
  return request.get(`/api/benchmarks/runs/${runId}`)
}

// 启动异步 Benchmark
export function runBenchmarkAsync(data) {
  return request.post('/api/benchmarks/run/async', data)
}