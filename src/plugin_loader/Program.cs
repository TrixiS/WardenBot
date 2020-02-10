using System.Threading.Tasks;

namespace PluginLoader
{
    class Program
    {
        public static async Task Main(string[] args)
        {
            var pluginLoader = new Loader(new AssemblyLoader());

            pluginLoader.RunPluginsFromPath(args[0]);

            await Task.Delay(-1);
        }
    }
}
