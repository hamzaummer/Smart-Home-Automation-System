import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import './App.css';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './components/ui/card';
import { Button } from './components/ui/button';
import { Input } from './components/ui/input';
import { Label } from './components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './components/ui/select';
import { Switch } from './components/ui/switch';
import { Badge } from './components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './components/ui/tabs';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from './components/ui/dialog';
import { Alert, AlertDescription } from './components/ui/alert';
import { Separator } from './components/ui/separator';
import { 
  Power, 
  Plus, 
  Settings, 
  Wifi, 
  Clock, 
  Activity, 
  Zap,
  Home,
  Calendar,
  BarChart3,
  Trash2,
  Edit,
  Play,
  Pause
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;
const WS_URL = BACKEND_URL.replace('https://', 'wss://').replace('http://', 'ws://');

function App() {
  // State management
  const [devices, setDevices] = useState([]);
  const [schedules, setSchedules] = useState([]);
  const [logs, setLogs] = useState([]);
  const [stats, setStats] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [ws, setWs] = useState(null);
  const [connected, setConnected] = useState(false);

  // Form states
  const [newDevice, setNewDevice] = useState({ name: '', room: '', gpio_pin: 18 });
  const [newSchedule, setNewSchedule] = useState({
    device_id: '',
    name: '',
    schedule_type: 'daily',
    target_state: 'on',
    trigger_time: '12:00',
    days_of_week: []
  });
  
  const [showAddDevice, setShowAddDevice] = useState(false);
  const [showAddSchedule, setShowAddSchedule] = useState(false);
  const [activeTab, setActiveTab] = useState('dashboard');

  // WebSocket connection
  const connectWebSocket = useCallback(() => {
    try {
      const websocket = new WebSocket(`${WS_URL}/ws`);
      
      websocket.onopen = () => {
        console.log('WebSocket connected');
        setConnected(true);
        setWs(websocket);
      };
      
      websocket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          
          if (data.type === 'device_update') {
            setDevices(prev => prev.map(device => 
              device.id === data.device_id 
                ? { ...device, ...data.data }
                : device
            ));
          } else if (data.type === 'status_update') {
            setDevices(prev => prev.map(device => {
              const update = data.devices.find(d => d.id === device.id);
              return update ? { ...device, ...update } : device;
            }));
          }
        } catch (e) {
          console.error('Error parsing WebSocket message:', e);
        }
      };
      
      websocket.onclose = () => {
        console.log('WebSocket disconnected');
        setConnected(false);
        setWs(null);
        // Attempt to reconnect after 3 seconds
        setTimeout(connectWebSocket, 3000);
      };
      
      websocket.onerror = (error) => {
        console.error('WebSocket error:', error);
      };
    } catch (error) {
      console.error('WebSocket connection error:', error);
    }
  }, [WS_URL]);

  // API functions
  const fetchData = async () => {
    try {
      const [devicesRes, schedulesRes, logsRes, statsRes] = await Promise.all([
        axios.get(`${API}/devices`),
        axios.get(`${API}/schedules`),
        axios.get(`${API}/logs?limit=50`),
        axios.get(`${API}/stats`)
      ]);
      
      setDevices(devicesRes.data);
      setSchedules(schedulesRes.data);
      setLogs(logsRes.data);
      setStats(statsRes.data);
      setError('');
    } catch (err) {
      setError('Failed to fetch data from server');
      console.error('Error fetching data:', err);
    } finally {
      setLoading(false);
    }
  };

  const controlDevice = async (deviceId, state) => {
    try {
      await axios.post(`${API}/devices/control`, {
        device_id: deviceId,
        state: state
      });
      setError('');
    } catch (err) {
      setError('Failed to control device');
      console.error('Error controlling device:', err);
    }
  };

  const addDevice = async () => {
    try {
      await axios.post(`${API}/devices`, newDevice);
      setNewDevice({ name: '', room: '', gpio_pin: 18 });
      setShowAddDevice(false);
      fetchData();
    } catch (err) {
      setError('Failed to add device');
      console.error('Error adding device:', err);
    }
  };

  const deleteDevice = async (deviceId) => {
    try {
      await axios.delete(`${API}/devices/${deviceId}`);
      fetchData();
    } catch (err) {
      setError('Failed to delete device');
      console.error('Error deleting device:', err);
    }
  };

  const addSchedule = async () => {
    try {
      await axios.post(`${API}/schedules`, newSchedule);
      setNewSchedule({
        device_id: '',
        name: '',
        schedule_type: 'daily',
        target_state: 'on',
        trigger_time: '12:00',
        days_of_week: []
      });
      setShowAddSchedule(false);
      fetchData();
    } catch (err) {
      setError('Failed to add schedule');
      console.error('Error adding schedule:', err);
    }
  };

  const toggleSchedule = async (scheduleId) => {
    try {
      await axios.put(`${API}/schedules/${scheduleId}/toggle`);
      fetchData();
    } catch (err) {
      setError('Failed to toggle schedule');
      console.error('Error toggling schedule:', err);
    }
  };

  const deleteSchedule = async (scheduleId) => {
    try {
      await axios.delete(`${API}/schedules/${scheduleId}`);
      fetchData();
    } catch (err) {
      setError('Failed to delete schedule');
      console.error('Error deleting schedule:', err);
    }
  };

  // Effects
  useEffect(() => {
    fetchData();
    connectWebSocket();
  }, [connectWebSocket]);

  // Helper functions
  const formatTime = (timestamp) => {
    return new Date(timestamp).toLocaleTimeString();
  };

  const formatUptime = (seconds) => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    return `${hours}h ${minutes}m`;
  };

  const getStatusBadge = (status) => {
    const variants = {
      online: 'default',
      offline: 'destructive',
      error: 'destructive'
    };
    return <Badge variant={variants[status] || 'secondary'}>{status}</Badge>;
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-indigo-600 mx-auto"></div>
          <p className="mt-4 text-lg text-gray-600">Loading IoT Control System...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50">
      {/* Header */}
      <header className="bg-white/80 backdrop-blur-md border-b border-gray-200 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-gradient-to-r from-blue-600 to-indigo-600 rounded-lg">
                <Home className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-gray-900">IoT Home Automation</h1>
                <div className="flex items-center gap-2 text-sm text-gray-500">
                  <div className={`w-2 h-2 rounded-full ${connected ? 'bg-green-500' : 'bg-red-500'}`}></div>
                  {connected ? 'Connected' : 'Disconnected'}
                </div>
              </div>
            </div>
            
            <div className="flex items-center gap-4">
              <div className="hidden sm:flex items-center gap-4 text-sm text-gray-600">
                <div className="flex items-center gap-1">
                  <Activity className="w-4 h-4" />
                  <span>{stats.online_devices || 0}/{stats.total_devices || 0} Online</span>
                </div>
                <div className="flex items-center gap-1">
                  <Clock className="w-4 h-4" />
                  <span>{stats.active_schedules || 0} Schedules</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Error Alert */}
      {error && (
        <div className="max-w-7xl mx-auto px-4 pt-4">
          <Alert className="border-red-200 bg-red-50">
            <AlertDescription className="text-red-800">{error}</AlertDescription>
          </Alert>
        </div>
      )}

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid w-full grid-cols-4 max-w-md mx-auto mb-8">
            <TabsTrigger value="dashboard" className="flex items-center gap-2">
              <Home className="w-4 h-4" />
              Dashboard
            </TabsTrigger>
            <TabsTrigger value="schedules" className="flex items-center gap-2">
              <Clock className="w-4 h-4" />
              Schedules
            </TabsTrigger>
            <TabsTrigger value="logs" className="flex items-center gap-2">
              <Activity className="w-4 h-4" />
              Logs
            </TabsTrigger>
            <TabsTrigger value="stats" className="flex items-center gap-2">
              <BarChart3 className="w-4 h-4" />
              Stats
            </TabsTrigger>
          </TabsList>

          {/* Dashboard Tab */}
          <TabsContent value="dashboard">
            <div className="space-y-6">
              {/* Quick Stats */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                <Card className="bg-gradient-to-r from-blue-500 to-blue-600 text-white border-0">
                  <CardContent className="p-6">
                    <div className="flex items-center gap-3">
                      <Zap className="w-8 h-8" />
                      <div>
                        <p className="text-blue-100">Total Devices</p>
                        <p className="text-2xl font-bold">{stats.total_devices || 0}</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
                
                <Card className="bg-gradient-to-r from-green-500 to-green-600 text-white border-0">
                  <CardContent className="p-6">
                    <div className="flex items-center gap-3">
                      <Wifi className="w-8 h-8" />
                      <div>
                        <p className="text-green-100">Online</p>
                        <p className="text-2xl font-bold">{stats.online_devices || 0}</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
                
                <Card className="bg-gradient-to-r from-purple-500 to-purple-600 text-white border-0">
                  <CardContent className="p-6">
                    <div className="flex items-center gap-3">
                      <Clock className="w-8 h-8" />
                      <div>
                        <p className="text-purple-100">Active Schedules</p>
                        <p className="text-2xl font-bold">{stats.active_schedules || 0}</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
                
                <Card className="bg-gradient-to-r from-orange-500 to-orange-600 text-white border-0">
                  <CardContent className="p-6">
                    <div className="flex items-center gap-3">
                      <Activity className="w-8 h-8" />
                      <div>
                        <p className="text-orange-100">Runtime Hours</p>
                        <p className="text-2xl font-bold">{stats.total_runtime_hours || 0}</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>

              {/* Devices Grid */}
              <div className="flex justify-between items-center">
                <h2 className="text-2xl font-bold text-gray-900">Your Devices</h2>
                <Dialog open={showAddDevice} onOpenChange={setShowAddDevice}>
                  <DialogTrigger asChild>
                    <Button className="bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700">
                      <Plus className="w-4 h-4 mr-2" />
                      Add Device
                    </Button>
                  </DialogTrigger>
                  <DialogContent>
                    <DialogHeader>
                      <DialogTitle>Add New Device</DialogTitle>
                      <DialogDescription>
                        Configure a new IoT device to control
                      </DialogDescription>
                    </DialogHeader>
                    <div className="space-y-4">
                      <div>
                        <Label htmlFor="name">Device Name</Label>
                        <Input
                          id="name"
                          value={newDevice.name}
                          onChange={(e) => setNewDevice({...newDevice, name: e.target.value})}
                          placeholder="Living Room Light"
                        />
                      </div>
                      <div>
                        <Label htmlFor="room">Room</Label>
                        <Input
                          id="room"
                          value={newDevice.room}
                          onChange={(e) => setNewDevice({...newDevice, room: e.target.value})}
                          placeholder="Living Room"
                        />
                      </div>
                      <div>
                        <Label htmlFor="gpio">GPIO Pin</Label>
                        <Input
                          id="gpio"
                          type="number"
                          value={newDevice.gpio_pin}
                          onChange={(e) => setNewDevice({...newDevice, gpio_pin: parseInt(e.target.value)})}
                        />
                      </div>
                    </div>
                    <DialogFooter>
                      <Button onClick={addDevice} className="bg-gradient-to-r from-blue-600 to-indigo-600">
                        Add Device
                      </Button>
                    </DialogFooter>
                  </DialogContent>
                </Dialog>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {devices.map((device) => (
                  <Card key={device.id} className="hover:shadow-lg transition-all duration-300 border-0 bg-white/70 backdrop-blur-sm">
                    <CardHeader className="pb-4">
                      <div className="flex justify-between items-start">
                        <div>
                          <CardTitle className="text-lg">{device.name}</CardTitle>
                          <CardDescription className="text-gray-600">
                            {device.room} • GPIO {device.gpio_pin}
                          </CardDescription>
                        </div>
                        <div className="flex gap-2">
                          {getStatusBadge(device.status)}
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => deleteDevice(device.id)}
                            className="text-red-600 hover:bg-red-50"
                          >
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        </div>
                      </div>
                    </CardHeader>
                    
                    <CardContent className="space-y-4">
                      {/* Relay Control */}
                      <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                        <div className="flex items-center gap-3">
                          <Power className={`w-5 h-5 ${device.relay_state === 'on' ? 'text-green-600' : 'text-gray-400'}`} />
                          <span className="font-medium">
                            {device.relay_state === 'on' ? 'ON' : 'OFF'}
                          </span>
                        </div>
                        <Switch
                          checked={device.relay_state === 'on'}
                          onCheckedChange={(checked) => controlDevice(device.id, checked ? 'on' : 'off')}
                        />
                      </div>
                      
                      {/* Device Stats */}
                      <div className="grid grid-cols-2 gap-4 text-sm">
                        <div>
                          <p className="text-gray-500">Uptime</p>
                          <p className="font-medium">{formatUptime(device.uptime || 0)}</p>
                        </div>
                        <div>
                          <p className="text-gray-500">WiFi Signal</p>
                          <p className="font-medium">{device.wifi_signal || 0}%</p>
                        </div>
                        <div>
                          <p className="text-gray-500">Last Seen</p>
                          <p className="font-medium">{formatTime(device.last_seen)}</p>
                        </div>
                        <div>
                          <p className="text-gray-500">Runtime</p>
                          <p className="font-medium">{formatUptime(device.total_runtime || 0)}</p>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>

              {devices.length === 0 && (
                <Card className="text-center py-12">
                  <CardContent>
                    <Home className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                    <h3 className="text-lg font-medium text-gray-900 mb-2">No devices found</h3>
                    <p className="text-gray-600 mb-4">Get started by adding your first IoT device</p>
                    <Button onClick={() => setShowAddDevice(true)} className="bg-gradient-to-r from-blue-600 to-indigo-600">
                      <Plus className="w-4 h-4 mr-2" />
                      Add Your First Device
                    </Button>
                  </CardContent>
                </Card>
              )}
            </div>
          </TabsContent>

          {/* Schedules Tab */}
          <TabsContent value="schedules">
            <div className="space-y-6">
              <div className="flex justify-between items-center">
                <h2 className="text-2xl font-bold text-gray-900">Device Schedules</h2>
                <Dialog open={showAddSchedule} onOpenChange={setShowAddSchedule}>
                  <DialogTrigger asChild>
                    <Button className="bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700">
                      <Plus className="w-4 h-4 mr-2" />
                      Add Schedule
                    </Button>
                  </DialogTrigger>
                  <DialogContent className="max-w-md">
                    <DialogHeader>
                      <DialogTitle>Create Schedule</DialogTitle>
                      <DialogDescription>
                        Automate your device control
                      </DialogDescription>
                    </DialogHeader>
                    <div className="space-y-4">
                      <div>
                        <Label htmlFor="schedule-name">Schedule Name</Label>
                        <Input
                          id="schedule-name"
                          value={newSchedule.name}
                          onChange={(e) => setNewSchedule({...newSchedule, name: e.target.value})}
                          placeholder="Evening Lights"
                        />
                      </div>
                      <div>
                        <Label htmlFor="device-select">Device</Label>
                        <Select value={newSchedule.device_id} onValueChange={(value) => setNewSchedule({...newSchedule, device_id: value})}>
                          <SelectTrigger>
                            <SelectValue placeholder="Select a device" />
                          </SelectTrigger>
                          <SelectContent>
                            {devices.map(device => (
                              <SelectItem key={device.id} value={device.id}>
                                {device.name} ({device.room})
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                      <div>
                        <Label htmlFor="schedule-type">Type</Label>
                        <Select value={newSchedule.schedule_type} onValueChange={(value) => setNewSchedule({...newSchedule, schedule_type: value})}>
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="daily">Daily</SelectItem>
                            <SelectItem value="weekly">Weekly</SelectItem>
                            <SelectItem value="once">Once</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                      <div>
                        <Label htmlFor="target-state">Action</Label>
                        <Select value={newSchedule.target_state} onValueChange={(value) => setNewSchedule({...newSchedule, target_state: value})}>
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="on">Turn ON</SelectItem>
                            <SelectItem value="off">Turn OFF</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                      <div>
                        <Label htmlFor="trigger-time">Time</Label>
                        <Input
                          id="trigger-time"
                          type="time"
                          value={newSchedule.trigger_time}
                          onChange={(e) => setNewSchedule({...newSchedule, trigger_time: e.target.value})}
                        />
                      </div>
                    </div>
                    <DialogFooter>
                      <Button onClick={addSchedule} className="bg-gradient-to-r from-purple-600 to-pink-600">
                        Create Schedule
                      </Button>
                    </DialogFooter>
                  </DialogContent>
                </Dialog>
              </div>

              <div className="grid gap-4">
                {schedules.map((schedule) => {
                  const device = devices.find(d => d.id === schedule.device_id);
                  return (
                    <Card key={schedule.id} className="border-0 bg-white/70 backdrop-blur-sm">
                      <CardContent className="p-6">
                        <div className="flex justify-between items-start">
                          <div className="space-y-2">
                            <div className="flex items-center gap-3">
                              <h3 className="font-semibold text-lg">{schedule.name}</h3>
                              <Badge variant={schedule.is_active ? 'default' : 'secondary'}>
                                {schedule.is_active ? 'Active' : 'Inactive'}
                              </Badge>
                            </div>
                            <p className="text-gray-600">
                              {device ? device.name : 'Unknown Device'} • {schedule.schedule_type.charAt(0).toUpperCase() + schedule.schedule_type.slice(1)}
                            </p>
                            <div className="flex items-center gap-4 text-sm text-gray-500">
                              <span>⏰ {schedule.trigger_time}</span>
                              <span>🎯 Turn {schedule.target_state.toUpperCase()}</span>
                            </div>
                          </div>
                          <div className="flex gap-2">
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => toggleSchedule(schedule.id)}
                              className={schedule.is_active ? 'text-orange-600 hover:bg-orange-50' : 'text-green-600 hover:bg-green-50'}
                            >
                              {schedule.is_active ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
                            </Button>
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => deleteSchedule(schedule.id)}
                              className="text-red-600 hover:bg-red-50"
                            >
                              <Trash2 className="w-4 h-4" />
                            </Button>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  );
                })}
              </div>

              {schedules.length === 0 && (
                <Card className="text-center py-12">
                  <CardContent>
                    <Calendar className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                    <h3 className="text-lg font-medium text-gray-900 mb-2">No schedules created</h3>
                    <p className="text-gray-600 mb-4">Automate your devices with smart scheduling</p>
                    <Button onClick={() => setShowAddSchedule(true)} className="bg-gradient-to-r from-purple-600 to-pink-600">
                      <Plus className="w-4 h-4 mr-2" />
                      Create Your First Schedule
                    </Button>
                  </CardContent>
                </Card>
              )}
            </div>
          </TabsContent>

          {/* Logs Tab */}
          <TabsContent value="logs">
            <div className="space-y-6">
              <h2 className="text-2xl font-bold text-gray-900">Activity Logs</h2>
              
              <Card className="border-0 bg-white/70 backdrop-blur-sm">
                <CardContent className="p-0">
                  <div className="max-h-96 overflow-y-auto">
                    {logs.map((log, index) => (
                      <div key={log.id} className={`p-4 ${index !== logs.length - 1 ? 'border-b' : ''}`}>
                        <div className="flex justify-between items-start">
                          <div>
                            <p className="font-medium text-gray-900">
                              {log.action.replace('_', ' ').charAt(0).toUpperCase() + log.action.replace('_', ' ').slice(1)}
                            </p>
                            <p className="text-sm text-gray-600">
                              Device: {devices.find(d => d.id === log.device_id)?.name || 'Unknown'}
                            </p>
                            {log.old_state && log.new_state && (
                              <p className="text-sm text-gray-500">
                                {log.old_state} → {log.new_state}
                              </p>
                            )}
                          </div>
                          <div className="text-right text-sm text-gray-500">
                            <p>{formatTime(log.timestamp)}</p>
                            <p>via {log.triggered_by}</p>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>

              {logs.length === 0 && (
                <Card className="text-center py-12">
                  <CardContent>
                    <Activity className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                    <h3 className="text-lg font-medium text-gray-900 mb-2">No activity logs</h3>
                    <p className="text-gray-600">Device activity will appear here</p>
                  </CardContent>
                </Card>
              )}
            </div>
          </TabsContent>

          {/* Stats Tab */}
          <TabsContent value="stats">
            <div className="space-y-6">
              <h2 className="text-2xl font-bold text-gray-900">System Statistics</h2>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <Card className="border-0 bg-white/70 backdrop-blur-sm">
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <BarChart3 className="w-5 h-5" />
                      System Overview
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="flex justify-between">
                      <span className="text-gray-600">Total Devices</span>
                      <span className="font-semibold">{stats.total_devices || 0}</span>
                    </div>
                    <Separator />
                    <div className="flex justify-between">
                      <span className="text-gray-600">Online Devices</span>
                      <span className="font-semibold text-green-600">{stats.online_devices || 0}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">Offline Devices</span>
                      <span className="font-semibold text-red-600">{stats.offline_devices || 0}</span>
                    </div>
                    <Separator />
                    <div className="flex justify-between">
                      <span className="text-gray-600">Total Schedules</span>
                      <span className="font-semibold">{stats.total_schedules || 0}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">Active Schedules</span>
                      <span className="font-semibold text-blue-600">{stats.active_schedules || 0}</span>
                    </div>
                  </CardContent>
                </Card>
                
                <Card className="border-0 bg-white/70 backdrop-blur-sm">
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Zap className="w-5 h-5" />
                      Usage Statistics
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="flex justify-between">
                      <span className="text-gray-600">Total Runtime</span>
                      <span className="font-semibold">{stats.total_runtime_hours || 0} hours</span>
                    </div>
                    <Separator />
                    <div className="flex justify-between">
                      <span className="text-gray-600">System Uptime</span>
                      <span className="font-semibold text-green-600">{stats.system_uptime || '24/7'}</span>
                    </div>
                    <Separator />
                    <div className="flex justify-between">
                      <span className="text-gray-600">Connection Status</span>
                      <span className={`font-semibold ${connected ? 'text-green-600' : 'text-red-600'}`}>
                        {connected ? 'Connected' : 'Disconnected'}
                      </span>
                    </div>
                  </CardContent>
                </Card>
              </div>

              {/* Per-device stats */}
              <Card className="border-0 bg-white/70 backdrop-blur-sm">
                <CardHeader>
                  <CardTitle>Device Performance</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    {devices.map((device) => (
                      <div key={device.id} className="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
                        <div>
                          <p className="font-medium">{device.name}</p>
                          <p className="text-sm text-gray-600">{device.room}</p>
                        </div>
                        <div className="text-right">
                          <p className="text-sm font-medium">
                            Runtime: {formatUptime(device.total_runtime || 0)}
                          </p>
                          <p className="text-sm text-gray-600">
                            Uptime: {formatUptime(device.uptime || 0)}
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>
        </Tabs>
      </main>
    </div>
  );
}

export default App;