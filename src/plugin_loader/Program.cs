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
        private static Loader loader = new Loader(new AssemblyLoader());
        
        public static async Task Main(string[] args)
        {
            loader.RunPluginsFromPath(args[0]);

            var connector = new WardenConnector("127.0.0.1", 6969, args[1]);

            connector.OnCommandReceived += OnCommandReceived;
            connector.Start();
            
            await Task.Delay(-1);
        }

        private static void OnCommandReceived(object sender, ConnectorEventArgs e)
        {
            if (e.Command == "load_plugin")
            {
                loader.RunPluginsFromPath(e.Args[0]);
            }
        }
    }
}
