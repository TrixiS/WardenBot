using System;
using System.Diagnostics;
using System.Threading.Tasks;

 // TODO:
//    make one solution and repo for all plugins
//    one plugin -> one project

namespace PluginLoader
{
    class Program
    {
        public static async Task Main(string[] args)
        {
            var pluginLoader = new Loader(new AssemblyLoader());

            pluginLoader.RunPluginsFromPath(args[0]);

            var connector = new WardenConnector("127.0.0.1", 6969, args[1]);

            connector.OnCommandReceived += (sender, eventArgs) => Debug.WriteLine("Received command");
            connector.Start();
            
            await Task.Delay(-1);
        }
    }
}
