import java.io.*;
import java.net.*;
import java.util.*;

/*
 * Server to process ping requests over UDP. 
 * The server sits in an infinite loop listening for incoming UDP packets. 
 * When a packet comes in, the server simply sends the encapsulated data back to the client.
 */

public class PingClient
{
   private static final double LOSS_RATE = 0.3;
   private static final int AVERAGE_DELAY = 100;  // milliseconds

   public static void main(String[] args) throws Exception
   {
      // Get command line argument.
      if (args.length != 2) {
         System.out.println("Required arguments: host port");
         return;
      }


      //array for time 
      long rtt_array[] = new long[10];
      //intiailsie with -1
      for (int i = 0; i<10; i++){
         rtt_array[i] = -1;
      }

      //port num
      int port = Integer.parseInt(args[1]);
      InetAddress hostIPaddr = InetAddress.getByName(args[0]);


      // Create a datagram socket for receiving and sending UDP packets
      // through the port specified on the command line.
      DatagramSocket socket = new DatagramSocket();
      socket.setSoTimeout(1000); //set 1 second

      // Processing loop.
      for (int i = 0; i<10; i++) {
         long start = System.currentTimeMillis(); 
         // Create a datagram packet to hold incomming UDP packet.
         
         String str = "Ping to " + args[0]+ " seq = "+ i + " " + "\r\n";
         DatagramPacket request = new DatagramPacket(str.getBytes(), str.length(), hostIPaddr, port);

         // Block until the host receives a UDP packet.
         socket.send(request);
         
         // Print the recieved data.
         try {
            byte[] receiveData=new byte[1024];
            // receive from server
            DatagramPacket response = new DatagramPacket(new byte[1024], 1024);
            socket.receive(response);
            
            long rtt = System.currentTimeMillis() - start;
            rtt_array[i] = rtt;  //add to array 

            System.out.println(str + "rtt = " + rtt + "ms");
            //close the scoket
         } catch (SocketTimeoutException e){
            System.out.println(str+ "time out");
         }     
      }

      /*You will also need to report the minimum, maximum and the average 
      RTTs of all packets received successfully at the end of your program's output.*/ 
   
      Arrays.sort(rtt_array);
      long length = rtt_array.length; 
   
      long total = 0;
      long countLength = 0; 
      for (int i = 0; i<length; i++){
         if (rtt_array[i] != -1){
            total = total+rtt_array[i];
            countLength++; 
         }         
      }

      //getting min value 
      long min = 99999; 
      int index = 0;
      for (int i = 0; i<length; i++){
         if (rtt_array[i]<min && rtt_array[i]!=-1){
            min = rtt_array[i]; 
            index = i;
         }
      }

      long avg = total/countLength;
      int len = rtt_array.length;
      System.out.println("Min = " + rtt_array[index] + " Max = " + rtt_array[len-1] + " Avg = " + avg +  "\n");
   
      socket.close();
   }

   /* 
    * Print ping data to the standard output stream.
    */
   private static void printData(DatagramPacket request) throws Exception
   {
      // Obtain references to the packet's array of bytes.
      byte[] buf = request.getData();

      // Wrap the bytes in a byte array input stream,
      // so that you can read the data as a stream of bytes.
      ByteArrayInputStream bais = new ByteArrayInputStream(buf);

      // Wrap the byte array output stream in an input stream reader,
      // so you can read the data as a stream of characters.
      InputStreamReader isr = new InputStreamReader(bais);

      // Wrap the input stream reader in a bufferred reader,
      // so you can read the character data a line at a time.
      // (A line is a sequence of chars terminated by any combination of \r and \n.) 
      BufferedReader br = new BufferedReader(isr);

      // The message data is contained in a single line, so read this line.
      String line = br.readLine();

      // Print host address and data received from it.
      System.out.println(
         "Received from " + 
         request.getAddress().getHostAddress() + 
         ": " +
         new String(line) );
   }
}
