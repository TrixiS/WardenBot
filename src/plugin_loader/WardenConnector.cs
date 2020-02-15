#pragma warning disable CS4014

using System;
using System.Text;
using System.Net;
using System.Net.Sockets;
using System.Threading;
using System.Threading.Tasks;
using Newtonsoft.Json.Linq;

namespace PluginLoader
{
    internal class ConnectorEventArgs : EventArgs
    {
        internal string Command { get; set; }
        internal string[] Args { get; set; }
        internal Socket Socket { get; set; }
    }

    internal class WardenConnector
    {
        private const int KeyBufferSize = 1024;
        private const int CommandBufferSize = KeyBufferSize * 10;

        private readonly string ownerKey;
        private readonly TcpListener listener;
        private readonly CancellationTokenSource tokenSource;
        private readonly BufferStringDecoder stringDecoder;
        
        internal event EventHandler<ConnectorEventArgs> OnCommandReceived;

        internal WardenConnector(string ip, int port, string ownerKey)
        {
            this.listener = new TcpListener(IPAddress.Parse(ip), port);
            this.tokenSource = new CancellationTokenSource();
            this.stringDecoder = new BufferStringDecoder();
            this.ownerKey = ownerKey;
        }

        internal void Start()
        {
            this.listener.Start();
            Task.Run(async () => await this.ListenAsync(this.tokenSource.Token));
        }

        internal void Stop()
        {
            this.tokenSource.Cancel();
            this.listener.Stop();
        }
        
        private async Task ListenAsync(CancellationToken cancellationToken)
        {
            while (true)
            {
                if (cancellationToken.IsCancellationRequested)
                    return;
                
                Socket socket = await this.listener.AcceptSocketAsync();
                Task.Run(() => this.Operate(socket), cancellationToken);
            }
        }

        private void Operate(Socket socket)
        {
            string ReceiveString(int bufferSize)
            {
                byte[] data = new byte[bufferSize];
                int bytesCount = socket.Receive(data);
                return this.stringDecoder.DecodeString(bytesCount, data);
            }
            
            while (true)
            {
                string key = ReceiveString(KeyBufferSize);

                if (this.ownerKey != key)
                {
                    socket.Close();
                    return;
                }

                var json = JObject.Parse(ReceiveString(CommandBufferSize));

                this.OnCommandReceived?.Invoke(null, new ConnectorEventArgs
                {
                    Socket = socket,
                    Command = (string) json["Command"],
                    Args = json["Args"].ToObject<string[]>()
                });
            }
        }
    }

    class BufferStringDecoder
    {
        private static Decoder StringDecoder = Encoding.UTF8.GetDecoder();

        public string DecodeString(int bytesCount, byte[] buffer)
        {
            char[] chars = new char[bytesCount];
            StringDecoder.GetChars(buffer, 0, bytesCount, chars, 0);
            return new string(chars);
        }
    }
}