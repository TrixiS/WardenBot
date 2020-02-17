using System;
using System.Linq;
using System.Reflection;
using System.Threading.Tasks;

 // TODO:
//    make one solution and repo for all plugins
//    one plugin -> one project

// TODO:
//    make check for plugins if loaded
//    maybe add error send system

namespace PluginLoader
{
    static class Program
    {
        private static Loader loader = new Loader(new AssemblyLoader());
        private static WardenConnector connector;
        
        public static async Task Main(string[] args)
        {
            loader.RunPluginsFromPath(args[0]);

            connector = new WardenConnector("127.0.0.1", int.Parse(args[2]), args[1]);
            connector.OnCommandReceived += OnCommandReceived;
            connector.Start();
            
            await Task.Delay(-1);
        }

        private static void OnCommandReceived(object sender, ConnectorEventArgs e)
        {
            // TODO: kill command for all tasks
            switch (e.Command)
            {
                case ConnectorCommand.LoadPlugin:
                {
                    loader.RunPluginsFromPath(e.Args[0]);
                    break;
                }
                case ConnectorCommand.UnloadPlugin:
                {
                    Assembly source = Assembly.LoadFile(e.Args[0]);
                    Type pluginType = null;

                    if (e.Args.Length > 1)
                        pluginType = source.ExportedTypes.FirstOrDefault(t => t.Name == e.Args[1]);

                    loader.KillPluginExecution(source, pluginType);
                                    
                    break;
                }
                case ConnectorCommand.Kill:
                {
                    connector.Stop();
                    Environment.Exit(0);
                    break;
                }

                default: 
                    return;
            }
        }
    }
}