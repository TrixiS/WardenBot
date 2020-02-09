using System;
using System.IO;
using System.Linq;
using System.Threading;
using System.Reflection;
using System.Threading.Tasks;
using System.Collections.Generic;
using WardenAPI.Plugins;

namespace PluginLoader
{
    public class Loader
    {
        public readonly string PluginsFilePath;
        public IEnumerable<IPlugin> RegisteredPlugins => this.registeredPlugins.Select(p => p.Plugin);
        
        private readonly Dictionary<AssemblyPlugin, CancellationTokenSource> runningPlugins;
        private readonly List<AssemblyPlugin> registeredPlugins;
        private readonly AssemblyLoader assemblyLoader;

        public Loader(string pluginsPath, AssemblyLoader assemblyLoader)
        {
            this.PluginsFilePath = pluginsPath;
            this.assemblyLoader = assemblyLoader;
            this.registeredPlugins = new List<AssemblyPlugin>();
            this.runningPlugins = new Dictionary<AssemblyPlugin, CancellationTokenSource>();
        }

        private string[] GetPluginsPaths()
        {
            return Directory.GetFiles(this.PluginsFilePath, "*.dll");
        }
        
        private void KillPluginExecution(AssemblyPlugin plugin)
        {
            if (!this.runningPlugins.ContainsKey(plugin))
                return;

            this.runningPlugins[plugin].Cancel();
            this.runningPlugins.Remove(plugin);
        }

        private IEnumerable<AssemblyPlugin> GetPlugins(Assembly assembly)
        {
            var pluginsTypes = assembly.ExportedTypes.Where(t => t.GetInterface(nameof(IPlugin)) != null);

            if (!pluginsTypes.Any())
                return null;
            
            List<AssemblyPlugin> plugins = new List<AssemblyPlugin>();

            foreach (Type pluginType in pluginsTypes)
            {
                IPlugin plugin = (IPlugin) Activator.CreateInstance(pluginType);
                
                plugins.Add(new AssemblyPlugin
                {
                    Plugin = plugin,
                    PluginAssembly = assembly
                });
            }

            return plugins;
        }

        public void LoadPlugins(bool reload = false)
        {
            string[] paths = this.GetPluginsPaths();
            
            if (paths.Length == 0)
                throw new Exception($"No plugins found in {this.PluginsFilePath}");

            var assemblies = this.assemblyLoader.LoadAssemblies(paths).Where(a => a != null);

            this.registeredPlugins.Clear();

            foreach (Assembly assembly in assemblies)
            {
                var plugins = this.GetPlugins(assembly);

                if (plugins == null)
                    continue;

                foreach (var plugin in plugins)
                {
                    if (reload)
                        this.KillPluginExecution(plugin);
                    
                    this.registeredPlugins.Add(plugin);
                }
            }
        }
        
        public async Task RunAsync()
        {
            foreach (var plugin in this.registeredPlugins)
            {
                var tokenSource = new CancellationTokenSource();
                
                Task pluginTask = Task.Run(async () =>
                {
                    await plugin.Plugin.RunAsync(tokenSource.Token);

                    if (this.runningPlugins.ContainsKey(plugin))
                        this.runningPlugins.Remove(plugin);
                });
                
                this.runningPlugins[plugin] = tokenSource;
            }
            
            await Task.Yield();
        }
    }
}