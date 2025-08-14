#!/usr/bin/env python3
"""
IoT Home Automation System - Backend API Testing
Tests all backend endpoints and functionality
"""

import requests
import json
import sys
import time
from datetime import datetime
from typing import Dict, Any, Optional

class IoTBackendTester:
    def __init__(self, base_url="https://iot-switch-control.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.created_devices = []
        self.created_schedules = []

    def log_test(self, name: str, success: bool, message: str = ""):
        """Log test results"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name}: PASSED {message}")
        else:
            print(f"❌ {name}: FAILED {message}")
        return success

    def make_request(self, method: str, endpoint: str, data: Optional[Dict] = None, expected_status: int = 200) -> tuple[bool, Dict]:
        """Make HTTP request and return success status and response data"""
        url = f"{self.api_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=10)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers, timeout=10)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=10)
            else:
                return False, {"error": f"Unsupported method: {method}"}

            success = response.status_code == expected_status
            try:
                response_data = response.json()
            except:
                response_data = {"status_code": response.status_code, "text": response.text}
            
            return success, response_data

        except requests.exceptions.RequestException as e:
            return False, {"error": str(e)}

    def test_api_root(self):
        """Test API root endpoint"""
        success, data = self.make_request('GET', '')
        return self.log_test(
            "API Root", 
            success and "IoT Home Automation System API" in str(data),
            f"Response: {data}"
        )

    def test_create_device(self):
        """Test device creation"""
        device_data = {
            "name": f"Test Device {datetime.now().strftime('%H%M%S')}",
            "device_type": "relay",
            "room": "Test Room",
            "gpio_pin": 18
        }
        
        success, data = self.make_request('POST', 'devices', device_data, 200)
        
        if success and 'id' in data:
            self.created_devices.append(data['id'])
            return self.log_test(
                "Create Device", 
                True,
                f"Created device with ID: {data['id']}"
            )
        else:
            return self.log_test(
                "Create Device", 
                False,
                f"Failed to create device: {data}"
            )

    def test_get_devices(self):
        """Test getting all devices"""
        success, data = self.make_request('GET', 'devices')
        
        if success and isinstance(data, list):
            return self.log_test(
                "Get Devices", 
                True,
                f"Retrieved {len(data)} devices"
            )
        else:
            return self.log_test(
                "Get Devices", 
                False,
                f"Failed to get devices: {data}"
            )

    def test_get_single_device(self):
        """Test getting a single device"""
        if not self.created_devices:
            return self.log_test("Get Single Device", False, "No devices to test with")
        
        device_id = self.created_devices[0]
        success, data = self.make_request('GET', f'devices/{device_id}')
        
        if success and data.get('id') == device_id:
            return self.log_test(
                "Get Single Device", 
                True,
                f"Retrieved device: {data.get('name')}"
            )
        else:
            return self.log_test(
                "Get Single Device", 
                False,
                f"Failed to get device {device_id}: {data}"
            )

    def test_update_device(self):
        """Test updating a device"""
        if not self.created_devices:
            return self.log_test("Update Device", False, "No devices to test with")
        
        device_id = self.created_devices[0]
        update_data = {
            "name": f"Updated Test Device {datetime.now().strftime('%H%M%S')}",
            "room": "Updated Room"
        }
        
        success, data = self.make_request('PUT', f'devices/{device_id}', update_data)
        
        if success and data.get('name') == update_data['name']:
            return self.log_test(
                "Update Device", 
                True,
                f"Updated device name to: {data.get('name')}"
            )
        else:
            return self.log_test(
                "Update Device", 
                False,
                f"Failed to update device: {data}"
            )

    def test_control_device(self):
        """Test device control"""
        if not self.created_devices:
            return self.log_test("Control Device", False, "No devices to test with")
        
        device_id = self.created_devices[0]
        control_data = {
            "device_id": device_id,
            "state": "on"
        }
        
        success, data = self.make_request('POST', 'devices/control', control_data)
        
        if success:
            # Wait a moment for the state to update
            time.sleep(1)
            return self.log_test(
                "Control Device", 
                True,
                f"Successfully controlled device: {data.get('message', '')}"
            )
        else:
            return self.log_test(
                "Control Device", 
                False,
                f"Failed to control device: {data}"
            )

    def test_create_schedule(self):
        """Test schedule creation"""
        if not self.created_devices:
            return self.log_test("Create Schedule", False, "No devices to test with")
        
        schedule_data = {
            "device_id": self.created_devices[0],
            "name": f"Test Schedule {datetime.now().strftime('%H%M%S')}",
            "schedule_type": "daily",
            "target_state": "on",
            "trigger_time": "12:00"
        }
        
        success, data = self.make_request('POST', 'schedules', schedule_data)
        
        if success and 'id' in data:
            self.created_schedules.append(data['id'])
            return self.log_test(
                "Create Schedule", 
                True,
                f"Created schedule with ID: {data['id']}"
            )
        else:
            return self.log_test(
                "Create Schedule", 
                False,
                f"Failed to create schedule: {data}"
            )

    def test_get_schedules(self):
        """Test getting all schedules"""
        success, data = self.make_request('GET', 'schedules')
        
        if success and isinstance(data, list):
            return self.log_test(
                "Get Schedules", 
                True,
                f"Retrieved {len(data)} schedules"
            )
        else:
            return self.log_test(
                "Get Schedules", 
                False,
                f"Failed to get schedules: {data}"
            )

    def test_toggle_schedule(self):
        """Test toggling schedule active status"""
        if not self.created_schedules:
            return self.log_test("Toggle Schedule", False, "No schedules to test with")
        
        schedule_id = self.created_schedules[0]
        success, data = self.make_request('PUT', f'schedules/{schedule_id}/toggle')
        
        if success:
            return self.log_test(
                "Toggle Schedule", 
                True,
                f"Successfully toggled schedule: {data.get('message', '')}"
            )
        else:
            return self.log_test(
                "Toggle Schedule", 
                False,
                f"Failed to toggle schedule: {data}"
            )

    def test_get_logs(self):
        """Test getting device logs"""
        success, data = self.make_request('GET', 'logs?limit=10')
        
        if success and isinstance(data, list):
            return self.log_test(
                "Get Logs", 
                True,
                f"Retrieved {len(data)} log entries"
            )
        else:
            return self.log_test(
                "Get Logs", 
                False,
                f"Failed to get logs: {data}"
            )

    def test_get_stats(self):
        """Test getting system statistics"""
        success, data = self.make_request('GET', 'stats')
        
        expected_keys = ['total_devices', 'online_devices', 'total_schedules', 'active_schedules']
        has_expected_keys = all(key in data for key in expected_keys)
        
        if success and has_expected_keys:
            return self.log_test(
                "Get Stats", 
                True,
                f"Stats: {data.get('total_devices', 0)} devices, {data.get('online_devices', 0)} online"
            )
        else:
            return self.log_test(
                "Get Stats", 
                False,
                f"Failed to get stats or missing keys: {data}"
            )

    def test_websocket_endpoint(self):
        """Test WebSocket endpoint availability (basic connectivity test)"""
        try:
            # Test if WebSocket endpoint is accessible by making HTTP request to it
            # This will fail but should return a specific WebSocket upgrade error
            ws_url = f"{self.base_url}/ws"
            response = requests.get(ws_url, timeout=5)
            
            # WebSocket endpoints typically return 426 Upgrade Required or similar
            if response.status_code in [400, 426] or "websocket" in response.text.lower():
                return self.log_test(
                    "WebSocket Endpoint", 
                    True,
                    "WebSocket endpoint is accessible"
                )
            else:
                return self.log_test(
                    "WebSocket Endpoint", 
                    False,
                    f"Unexpected response: {response.status_code}"
                )
        except Exception as e:
            return self.log_test(
                "WebSocket Endpoint", 
                False,
                f"Error accessing WebSocket: {str(e)}"
            )

    def cleanup(self):
        """Clean up created test data"""
        print("\n🧹 Cleaning up test data...")
        
        # Delete created schedules
        for schedule_id in self.created_schedules:
            success, _ = self.make_request('DELETE', f'schedules/{schedule_id}', expected_status=200)
            if success:
                print(f"✅ Deleted schedule {schedule_id}")
            else:
                print(f"❌ Failed to delete schedule {schedule_id}")
        
        # Delete created devices
        for device_id in self.created_devices:
            success, _ = self.make_request('DELETE', f'devices/{device_id}', expected_status=200)
            if success:
                print(f"✅ Deleted device {device_id}")
            else:
                print(f"❌ Failed to delete device {device_id}")

    def run_all_tests(self):
        """Run all backend tests"""
        print("🚀 Starting IoT Home Automation Backend Tests")
        print(f"🌐 Testing API at: {self.api_url}")
        print("=" * 60)
        
        # Basic API tests
        self.test_api_root()
        
        # Device management tests
        self.test_create_device()
        self.test_get_devices()
        self.test_get_single_device()
        self.test_update_device()
        self.test_control_device()
        
        # Schedule management tests
        self.test_create_schedule()
        self.test_get_schedules()
        self.test_toggle_schedule()
        
        # Logging and stats tests
        self.test_get_logs()
        self.test_get_stats()
        
        # WebSocket test
        self.test_websocket_endpoint()
        
        # Cleanup
        self.cleanup()
        
        # Final results
        print("\n" + "=" * 60)
        print(f"📊 Test Results: {self.tests_passed}/{self.tests_run} tests passed")
        
        if self.tests_passed == self.tests_run:
            print("🎉 All tests passed! Backend is working correctly.")
            return 0
        else:
            failed_tests = self.tests_run - self.tests_passed
            print(f"⚠️  {failed_tests} test(s) failed. Please check the backend implementation.")
            return 1

def main():
    """Main test execution"""
    tester = IoTBackendTester()
    return tester.run_all_tests()

if __name__ == "__main__":
    sys.exit(main())