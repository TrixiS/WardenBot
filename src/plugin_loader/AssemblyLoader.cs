using System;
using System.Reflection;

namespace PluginLoader
{
    public class AssemblyLoader
    {
        public Assembly[] LoadAssemblies(string[] paths)
        {   
            var assemblies = new Assembly[paths.Length];

            for (int i = 0; i < paths.Length; i++)
                assemblies[i] = Assembly.LoadFrom(paths[i]);

            return assemblies;
        }
    }
}