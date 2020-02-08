using System.Threading.Tasks;

namespace PluginLoader
{
    class Program
    {
        public static async Task Main(string[] args)
        {
            var pluginLoader = new Loader(args[0], new AssemblyLoader());

            pluginLoader.LoadPlugins();
            await pluginLoader.RunAsync();
            await Task.Delay(-1);
        }
    }
}
