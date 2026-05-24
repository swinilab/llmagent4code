# JMeter Performance Testing Guide

_Testing React + TypeScript Backend Performance_

## Overview

This guide covers performance testing your local React frontend + TypeScript backend using **Apache JMeter 5.6.3**. JMeter targets backend APIs (HTTP requests, DB, WebSocket) rather than React UI directly.

## Prerequisites

### macOS

- Apache JMeter 5.6.3 installed
- Java 8+ (required for JMeter)

### Windows

- Download JMeter from [Apache JMeter](https://jmeter.apache.org/download_jmeter.cgi)
- Extract to desired location (e.g., `C:\jmeter`)
- Java 8+ installed
- Run via `bin\jmeter.bat`

### Linux

- Download JMeter tarball
- Extract: `tar -xzf apache-jmeter-5.6.3.tgz`
- Java 8+ installed: `sudo apt install openjdk-11-jdk` (Ubuntu/Debian)
- Run via `bin/jmeter.sh`

## Step-by-Step Setup

### 1. Start Your Application

Ensure both services are running locally:

- **React Frontend**: `http://localhost:3000` (default)
- **TypeScript Backend**: `http://localhost:4000` (or configured port)

### 2. Create Test Plan

1. Open JMeter
2. Right-click **Test Plan** → Add → **Threads (Users)** → **Thread Group**

### 3. Configure Thread Group

Set load parameters:

- **Number of Threads (users)**: `50` (simulates 50 concurrent users)
- **Ramp-Up Period (seconds)**: `10` (users start over 10 seconds)
- **Loop Count**: `5` (each user makes 5 requests)

### 4. Add HTTP Request Sampler

1. Right-click **Thread Group** → Add → **Sampler** → **HTTP Request**
2. Configure:
   - **Server Name or IP**: `localhost`
   - **Port Number**: `4000` (your backend port)
   - **Method**: `GET` or `POST`
   - **Path**: `/api/your-endpoint`
   - For POST requests: add JSON body data

### 5. Add HTTP Headers (Optional)

For APIs requiring specific headers:

1. Right-click **HTTP Request** → Add → **Config Element** → **HTTP Header Manager**
2. Add headers:
   ```
   Content-Type: application/json
   Authorization: Bearer <your-token>
   ```

### 6. Add Result Listeners

Monitor test results:

- Right-click **Thread Group** → Add → **Listener**
- Recommended listeners:
  - **View Results Tree**: Detailed request/response logs
  - **Summary Report**: Average response time, throughput, error rate
  - **Graph Results**: Visual performance trends

### 7. Execute Test

1. Save test plan: **File** → **Save As**
2. Click green **Start** button (▶)
3. Monitor listeners for real-time results

### 8. Analyze Results

Key metrics to evaluate:

- **Average Response Time**: Backend processing speed
- **Throughput (req/sec)**: Backend capacity under load
- **Error Rate (%)**: Failed requests (500 errors, timeouts)
- **95th Percentile**: Response time for slowest 5% of requests

## Platform-Specific Notes

### macOS

- JMeter GUI may require increased heap: `export JVM_ARGS="-Xms1024m -Xmx2048m"`
- Use Activity Monitor to check system resources during tests

### Windows

- Modify `bin\jmeter.bat` for heap settings: `set HEAP=-Xms1g -Xmx2g`
- Use Task Manager to monitor resource usage
- Windows Defender may slow JMeter - add exception for JMeter folder

### Linux

- Increase system limits for high concurrent users:
  ```bash
  ulimit -n 65536  # file descriptors
  echo 'net.core.somaxconn = 65536' >> /etc/sysctl.conf
  ```
- Use `htop` to monitor system resources

## Advanced Configuration

### Database Testing

- Add **JDBC Request** sampler for direct DB performance testing
- Configure connection pool in **JDBC Connection Configuration**

### WebSocket Testing

- Use **WebSocket Sampler** plugin for real-time communication testing

### Load Profiles

- **Stress Test**: Gradually increase load until failure
- **Spike Test**: Sudden load increases
- **Endurance Test**: Sustained load over extended periods

## Troubleshooting

### Common Issues

- **Connection refused**: Verify backend is running on specified port
- **High response times**: Check system resources (CPU, memory)
- **SSL errors**: Add SSL certificate or disable SSL verification

### Performance Tips

- Run JMeter in non-GUI mode for large tests: `jmeter -n -t testplan.jmx -l results.jtl`
- Use CSV output for better performance than GUI listeners
- Monitor both client (JMeter) and server resources during testing

## Important Notes

⚠️ **Limitations**:

- JMeter tests backend APIs, not React UI rendering
- For frontend performance, use browser-based tools (Lighthouse, WebPageTest)
- For UI automation with load, combine Selenium/Playwright with JMeter

✅ **Best Practices**:

- Start with small load, gradually increase
- Test on production-like environment when possible
- Monitor server logs during testing
- Document baseline performance metrics
