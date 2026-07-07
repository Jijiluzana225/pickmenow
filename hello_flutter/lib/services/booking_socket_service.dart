import 'dart:convert';
import 'package:web_socket_channel/web_socket_channel.dart';

class BookingSocketService {
  WebSocketChannel? _channel;

  void connect({
    required int bookingId,
    required Function(Map<String, dynamic>) onMessage,
  }) {
    final url = Uri.parse(
      'ws://127.0.0.1:8000/ws/booking/$bookingId/',
    );

    _channel = WebSocketChannel.connect(url);

    _channel!.stream.listen((message) {
      final data = jsonDecode(message);
      onMessage(data);
    });
  }

  void disconnect() {
    _channel?.sink.close();
  }
}