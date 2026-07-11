import 'package:flutter/material.dart';
import 'services/booking_socket_service.dart';

void main() {
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'PickMeNow',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.orange),
        useMaterial3: true,
      ),
      home: const BookingNotificationTestScreen(),
    );
  }
}

class BookingNotificationTestScreen extends StatefulWidget {
  const BookingNotificationTestScreen({super.key});

  @override
  State<BookingNotificationTestScreen> createState() =>
      _BookingNotificationTestScreenState();
}

class _BookingNotificationTestScreenState
    extends State<BookingNotificationTestScreen> {
  final TextEditingController _bookingIdController = TextEditingController();
  final BookingSocketService _socketService = BookingSocketService();

  String _status = 'Not connected';
  bool _isAccepted = false;

  void _connectToBooking() {
    final bookingId = int.tryParse(_bookingIdController.text.trim());

    if (bookingId == null) {
      setState(() {
        _status = 'Please enter a valid booking ID';
      });
      return;
    }

    setState(() {
      _status = 'Listening to booking #$bookingId...';
      _isAccepted = false;
    });

    _socketService.connect(
      bookingId: bookingId,
      onMessage: (data) {
        if (data['type'] == 'booking_accepted') {
          setState(() {
            _status = 'Your booking has been accepted!';
            _isAccepted = true;
          });

          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('Your PickMeNow booking has been accepted!'),
              duration: Duration(seconds: 5),
            ),
          );
        }
      },
    );
  }

  @override
  void dispose() {
    _socketService.disconnect();
    _bookingIdController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('PickMeNow Notification Test'),
      ),
      body: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              _isAccepted ? Icons.check_circle : Icons.notifications_active,
              size: 90,
              color: _isAccepted ? Colors.green : Colors.orange,
            ),
            const SizedBox(height: 20),
            Text(
              _status,
              textAlign: TextAlign.center,
              style: const TextStyle(fontSize: 22),
            ),
            const SizedBox(height: 30),
            TextField(
              controller: _bookingIdController,
              keyboardType: TextInputType.number,
              decoration: const InputDecoration(
                labelText: 'Booking ID',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 20),
            ElevatedButton.icon(
              onPressed: _connectToBooking,
              icon: const Icon(Icons.wifi),
              label: const Text('Listen for Acceptance'),
            ),
          ],
        ),
      ),
    );
  }
}