using System.Reflection;
using WardenAPI.Plugins;

namespace PluginLoader
{
    public class AssemblyPlugin
    {
        public Assembly PluginAssembly { get; set; }
        public IPlugin Plugin { get; set; }

        public bool Equals(AssemblyPlugin other)
        {
            return other?.PluginAssembly == this?.PluginAssembly && 
                   other?.Plugin.GetType() == this?.Plugin.GetType();
        }
    }
}