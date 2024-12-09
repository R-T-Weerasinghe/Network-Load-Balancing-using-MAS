from mesa import Agent, Model
from mesa.space import MultiGrid
from mesa.time import RandomActivation
from mesa.visualization.modules import CanvasGrid, ChartModule
from mesa.visualization.UserParam import UserSettableParameter
from mesa.visualization.ModularVisualization import ModularServer
from mesa.datacollection import DataCollector
import random
from mesa.time import BaseScheduler


class UserAgent(Agent):
    """User requesting connection to a server."""

    def __init__(self, unique_id, model):
        super().__init__(unique_id, model)
        self.myid = unique_id
        self.connected_to = None  # Server ID or None
        self.steps_to_live = random.randint(10, 20)
        self.steps_alive = 0
        self.connection_requested = False
        self.connection_approved = False
        # self.connection_rejected = False
        self.wait_steps = 0
        self.state = "disconnected"

    def request_connection(self):
        """Request connection to a server."""
        target_server = random.choice(self.model.server_agents)
        # NEW COdes
        msg = f"COMM: User {self.myid} requesting connection to Server {target_server.unique_id}"
        self.model.visualizer.add_log_message(msg)
        # End 
        self.connection_requested = True
        target_server.receive_request(self)
        self.state = "requested"

    # Not used currently
    def receive_server_response(self, response):
        """Handle server response to connection request."""
        if response:
            self.connection_approved = True
            self.connected_to = response
            self.state = "connected"
            self.send_greeting()

    def send_greeting(self):
        """Send a greeting to the server."""
        if self.connected_to:
            target_server = next(
                s for s in self.model.server_agents if s.unique_id == self.connected_to)
            target_server.receive_message(self)

    def get_server(self):
        """Get the server this user is connected to."""
        if self.connected_to is None:
            return None
        return next(s for s in self.model.server_agents if s.unique_id == self.connected_to)

    def check_connection(self):
        """Check if the connection is still alive."""
        if self.connected_to is None:
            return
        server = self.get_server()
        # if self.steps_alive >= self.steps_to_live:
        #     self.disconnect()   #
        if server is None or not server.active:
            # self.disconnect() #
            self.handle_disconnection()

    def handle_disconnection(self):
        """Handle disconnection from server."""
        self.connected_to = None
        self.connection_requested = False
        self.connection_approved = False
        # self.connection_rejected = False
        self.state = "disconnected"
        self.wait_steps = 10

    def die(self):
        """Die"""
        # print(f"User {self.myid} died")
        server = self.get_server()
        if server:
            server.handle_user_dies(self)
        self.model.users_died_this_step += 1
        self.model.schedule.remove(self)
        self.model.user_agents.remove(self)

    def step(self):
        """Advance the agent by one step."""
        # If not connected and not waiting, request connection
        if not self.connected_to and not self.connection_requested and self.wait_steps == 0:
            self.request_connection()

        # If waiting after disconnection
        elif self.wait_steps > 0:
            self.wait_steps -= 1
            if self.wait_steps == 0 and not self.connected_to:
                self.connection_requested = False  # Retry connection

        # If connected, process step
        elif self.connected_to:
            self.check_connection()
            if self.connected_to:   # If still connected
                self.steps_alive += 1
                if self.steps_alive >= self.steps_to_live:
                    self.die()


class ServerAgent(Agent):
    """Server that handles user requests."""

    def __init__(self, unique_id, model, max_capacity=10):
        super().__init__(unique_id, model)
        self.max_capacity = max_capacity
        self.current_load = 0
        self.active = True
        self.connected_users = []
        self.upper_threshold = int(self.max_capacity * 0.6)

    def trigger_butterfly_effect(self):
        """Small change that causes cascading effects."""
        # Small trigger - disconnect one random user
        if self.connected_users:
            user = random.choice(list(self.connected_users))
            self.connected_users.remove(user)
            user.handle_disconnection()
            
            msg = f"BUTTERFLY: Small change - User {user.myid} disconnected from Server {self.unique_id}"
            self.model.visualizer.add_log_message(msg)
            
            # This may cause:
            # 1. Server becomes underutilized -> requests users
            # 2. Other servers transfer users -> they become underutilized
            # 3. Chain of load balancing begins
            # 4. Possible server terminations
            # 5. User redistribution across network


    def check_utilization(self):
        """Check if server is underutilized."""
        current_users = len(self.connected_users)
        half_capacity = self.max_capacity / 2
        target_users = self.upper_threshold
        # If underutilized, return True and number of users to add
        return current_users < half_capacity, target_users - current_users

    def request_users_from_others(self, users_needed):
        """Request users from other servers to improve utilization."""
        # New codes
        msg = f"COLLAB: Server {self.unique_id} requesting {users_needed} users"
        self.model.visualizer.add_log_message(msg)
        # End
        
        other_servers = [s for s in self.model.server_agents
                         if s != self and s.active]

        # NOTE: Potential infinite loop, handle with care
        while users_needed > 0 and other_servers:
            # Pick random server
            donor = random.choice(other_servers)

            # Check if donor has excess capacity
            donor_users = len(donor.connected_users)
            excess = donor_users - self.upper_threshold

            if excess > 0:
                # Transfer one random user
                # if donor.connected_users:   # This check is redundant
                for _ in range(random.randint(0, excess)):
                    user = random.choice(list(donor.connected_users))
                    self.transfer_user(user, donor)
                    users_needed -= 1

            # NOTE: this prevents infinite loop
            other_servers.remove(donor)


    def transfer_user(self, user, from_server):
        """Transfer a user from another server to this one."""
        # New codes
        msg = f"TRANSFER: User {user.myid} from S{from_server.unique_id} to S{self.unique_id}"
        self.model.visualizer.add_log_message(msg)
        # end

        # Remove from old server
        from_server.connected_users.remove(user)
        from_server.current_load -= 1

        # Add to this server
        self.connected_users.append(user)
        self.current_load += 1

        # Update user's connection
        user.connected_to = self.unique_id

    def check_severe_underutilization(self):
        """Check if server is severely underutilized."""
        return len(self.connected_users) < (self.max_capacity * 0.3)

    def can_others_handle_load(self):
        """Check if other servers can handle current users."""
        other_servers = [s for s in self.model.server_agents
                         if s != self and s.active]

        if not other_servers:
            return False  # Don't terminate if last server

        total_available = sum(
            self.upper_threshold - len(s.connected_users)
            for s in other_servers
        )
        return total_available >= len(self.connected_users)

    def distribute_users_and_terminate(self):
        """Distribute users evenly and terminate self."""
        # New codes
        msg = f"NEGO: Server {self.unique_id} negotiating shutdown"
        self.model.visualizer.add_log_message(msg)
        # end

        other_servers = [s for s in self.model.server_agents
                         if s != self and s.active]

        users_to_distribute = list(self.connected_users)
        while users_to_distribute:
            # Find server with lowest load percentage
            target_server = min(
                other_servers,
                key=lambda s: len(s.connected_users) / s.max_capacity
            )

            # Transfer one user
            user = users_to_distribute.pop()
            target_server.transfer_user(user, self)

        # Mark server as inactive
        self.active = False
        self.model.servers_died_this_step += 1
        # print(f"Server {self.unique_id} terminated due to underutilization")
        self.model.schedule.remove(self)
        self.model.server_agents.remove(self)

    def handle_user_dies(self, user):
        """Handle user death."""
        self.current_load -= 1
        self.connected_users.remove(user)

    def receive_request(self, user):
        """Handle user request, either connect or balance load."""
        if self.current_load < self.max_capacity:  # If server can take the load
            self.connect_user(user)
        else:
            # Communicate with other servers to balance the load
            self.balance_load(user)

    def receive_message(self, user):
        """Receive a message from a user."""
        print(f"Server {self.unique_id} received message from User {
              user.unique_id}")

    def connect_user(self, user):
        """Connect a user to this server."""
        print(f"test user: {user.unique_id}")
        print(f"test server: {self.unique_id}")
        user.receive_server_response(self.unique_id)
        self.current_load += 1
        self.connected_users.append(user)

    def balance_load(self, user):
        """Negotiate with other servers to balance the load."""
        other_servers = [
            s for s in self.model.server_agents if s != self and s.active]
        for server in other_servers:
            if server.current_load < server.max_capacity:
                server.connect_user(user)
                return
        # If no servers can take the load, spawn a new server
        self.model.spawn_server()
        # New server handles the user
        self.model.server_agents[-1].connect_user(user)

    def step(self):
        """Execute one step."""
        if self.active:
            # Check severe underutilization
            if self.check_severe_underutilization():
                # First try to get users from other servers
                is_underutilized, users_needed = self.check_utilization()
                if is_underutilized:
                    self.request_users_from_others(users_needed)

                # If still severely underutilized and others can handle load
                if self.check_severe_underutilization() and self.can_others_handle_load():
                    self.distribute_users_and_terminate()
                    return

        # if not self.active:
        #     if random.random() < self.model.server_up_chance:
        #         self.active = True
        # # Handle server failure randomly (if not manual)
        # if random.random() < self.model.server_failure_chance:
        #     self.active = False
        #     self.model.handle_server_failure(self)


class LoadBalancerModel(Model):
    """Model for load balancing with user and server agents."""

    def __init__(
        self,
        visualizer,
        initial_users=20,
        initial_servers=4,
        max_server_capacity=10,
        server_failure_chance=0.1,
        server_up_chance=0.1,
        max_users=100,
        min_users=10,
        user_spawn_chance=0.5
    ):
        self.initial_users = initial_users
        self.server_failure_chance = server_failure_chance
        self.server_up_chance = server_up_chance
        self.max_server_capacity = max_server_capacity
        self.visualizer = visualizer

        class LoadBalancerScheduler(BaseScheduler):
            """Custom scheduler that activates agents in a specific order:
            1. Users first (to request connections/die)
            2. Servers second (to handle load balancing)
            """
            def step(self):
                """Execute the step of all agents, one at a time, in order."""
                for agent in self.agents:
                    if isinstance(agent, UserAgent):
                        agent.step()
                for agent in self.agents:
                    if isinstance(agent, ServerAgent):
                        agent.step()
                self.steps += 1
                self.time += 1

        # Replace the random activation with custom scheduler
        self.schedule = LoadBalancerScheduler(self)
        # self.grid = MultiGrid(20, 20, torus=True)
        self.server_agents = []
        self.user_agents = []
        self.min_users = min_users
        self.max_users = max_users
        self.user_spawn_chance = user_spawn_chance
        self.next_user_id = initial_users + 100  # Start IDs after initial batch
        self.next_server_id = initial_servers + 100

        # Add counters
        self.step_count = 0
        self.users_spawned_this_step = 0
        self.users_died_this_step = 0
        self.servers_spawned_this_step = 0
        self.servers_died_this_step = 0

        # # Create a DataCollector to track server loads
        # self.datacollector = DataCollector(
        #     {
        #         "Server Load": lambda m: [server.current_load for server in m.schedule.agents if isinstance(server, ServerAgent)]
        #     }
        # )

        self.summarycollector = DataCollector(
            model_reporters={
                "Step": lambda m: m.step_count,
                "Total Users": lambda m: len(m.user_agents),
                "Server Allocations": lambda m: m.get_server_allocations(),
                "New Users": lambda m: m.users_spawned_this_step,
                "Dead Users": lambda m: m.users_died_this_step,
                "New Servers": lambda m: m.servers_spawned_this_step,
                "Dead Servers": lambda m: m.servers_died_this_step
            }
        )

        # Create initial servers
        for _ in range(initial_servers):
            self.spawn_server()

        # Create users
        for _ in range(initial_users):
            self.spawn_user()

    def get_server_allocations(self):
        """Get current user allocation per server."""
        return {f"Server {s.unique_id}": len(s.connected_users)
                for s in self.server_agents if s.active}

    def spawn_user(self):
        """Create a new user agent."""
        user = UserAgent(self.next_user_id, self)
        # print(f"Spawning user with {self.next_user_id}")
        self.schedule.add(user)
        self.user_agents.append(user)
        self.users_spawned_this_step += 1  # Increment counter
        self.next_user_id += 1
        return user

    def maintain_population(self):
        """Check and maintain user population within bounds."""
        # Clean up dead users from list
        self.user_agents = [user for user in self.user_agents
                            if user in self.schedule.agents]

        current_users = len(self.user_agents)

        # Spawn new users if below minimum
        if current_users < self.min_users:
            users_to_add = self.min_users - current_users
            for _ in range(users_to_add):
                self.spawn_user()

        # Random chance to spawn new user if below max
        elif current_users < self.max_users and random.random() < self.user_spawn_chance:
            self.spawn_user()

        # Kill random user if above max
        elif current_users > self.max_users:
            user_to_kill = random.choice(self.user_agents)
            user_to_kill.die()

    def spawn_server(self):
        """Spawn a new server."""
        # id = len(self.server_agents)
        print(f"Spawning server with {self.next_server_id}")
        server = ServerAgent(self.next_server_id, self, max_capacity=self.max_server_capacity)
        self.schedule.add(server)   # add to scheduler (aka simulation)
        self.server_agents.append(server)
        self.servers_spawned_this_step += 1  # Increment counter
        self.next_server_id += 1
        return server

    def handle_server_failure(self, failed_server):
        """Redistribute users from a failed server."""
        users_to_reassign = [
            user for user in self.user_agents if user.connected_to == failed_server.unique_id]
        for user in users_to_reassign:
            user.handle_disconnection()

    def clean_user_agents(self):
        """Remove dead users from tracking list."""
        self.user_agents = [user for user in self.user_agents 
                           if user in self.schedule.agents]
        
    def step(self):
        """Execute one model step."""
        # Clean dead users first
        self.clean_user_agents()    # get the user agents in simulation
        self.maintain_population()  # spawn new users if below min
        self.schedule.step()    # execute step for all agents
        # Clean again after step
        self.clean_user_agents()

        # BUG: This is not working as expected, produces wrong counts sometimes
        # Verify consistency
        # assert len(self.user_agents) == sum(len(s.connected_users) 
        #        for s in self.server_agents if s.active), "User count mismatch!"
        
        # self.datacollector.collect(self)
        self.summarycollector.collect(self)

        # Reset counters
        self.step_count += 1
        self.users_spawned_this_step = 0
        self.users_died_this_step = 0
        self.servers_spawned_this_step = 0
        self.servers_died_this_step = 0

        # Print step summary
        data = self.summarycollector.model_vars
        print(f"\nStep {self.step_count}:")
        print(f"Total Users: {data['Total Users'][-1]}")
        print(f"Server Allocations: {data['Server Allocations'][-1]}")
        print(f"New Users: {data['New Users'][-1]}")
        print(f"Dead Users: {data['Dead Users'][-1]}")
        print(f"New Servers: {data['New Servers'][-1]}")
        print(f"Dead Servers: {data['Dead Servers'][-1]}")


# def agent_portrayal(agent):
#     """Visualization rules for agents."""
#     if isinstance(agent, UserAgent):
#         portrayal = {
#             "Shape": "circle",
#             "Filled": "true",
#             "r": 0.5,
#             "Color": "red" if agent.connected_to is None else "black",
#         }
#     elif isinstance(agent, ServerAgent):
#         portrayal = {
#             "Shape": "rect",
#             "Filled": "true",
#             "w": 0.8,
#             "h": 0.8,
#             "Color": "green" if agent.active else "gray",
#             "Layer": 1,
#             "text": f"{agent.current_load}/{agent.max_capacity}",
#             "text_color": "white",
#         }
#     return portrayal

# def network_portrayal(agent):
#     """Define visualization for agents."""
#     if agent is None:
#         return None
        
#     portrayal = {}
    
#     if isinstance(agent, ServerAgent):
#         portrayal = {
#             "Shape": "circle",
#             "r": 2,
#             "Layer": 1,
#             "Color": "red" if not agent.active else "green",
#             "Filled": True,
#             "text": f"S{agent.unique_id}\n({len(agent.connected_users)})",
#             "text_color": "white"
#         }
    
#     elif isinstance(agent, UserAgent):
#         color = "blue" if agent.connected_to is not None else "gray"
#         portrayal = {
#             "Shape": "circle",
#             "r": 0.2,
#             "Layer": 0,
#             "Color": color,
#             "Filled": True
#         }
        
#         # Add connection line if user is connected
#         if agent.connected_to is not None:
#             server = next((s for s in agent.model.server_agents 
#                          if s.unique_id == agent.connected_to), None)
#             if server:
#                 portrayal["Edge"] = {
#                     "Color": "yellow",
#                     "width": 2,
#                     "to_x": server.pos[0],
#                     "to_y": server.pos[1]
#                 }
    
#     return portrayal
# # Visualization Elements
# # grid = CanvasGrid(agent_portrayal, 20, 20, 500, 500)
# # In server.py or your main file:
# grid = CanvasGrid(
#     network_portrayal,
#     20, 20,  # grid size
#     500, 500  # pixel size
# )


# # server_chart = ChartModule(
# #     [{"Label": f"Server {i}", "Color": color}
# #         for i, color in enumerate(["blue", "orange", "green", "red", "purple"])],
# #     data_collector_name="datacollector",
# # )

# server_failure_slider = UserSettableParameter(
#     "slider",
#     "Server Failure Chance",
#     value=0.01,
#     min_value=0.0,
#     max_value=0.2,
#     step=0.01,
# )

# server_traffic_slider = UserSettableParameter(
#     "slider",
#     "Traffic Load (Users)",
#     value=20,
#     min_value=5,
#     max_value=100,
#     step=5,
# )

# server_capacity_slider = UserSettableParameter(
#     "slider",
#     "Server Capacity",
#     value=10,
#     min_value=5,
#     max_value=50,
#     step=5,
# )

# server_spawn_button = UserSettableParameter(
#     "static_text", value="Click Grid to Add Server")

# # Server
# server = ModularServer(
#     LoadBalancerModel,
#     [grid, server_chart],
#     "Load Balancer Simulation",
#     {
#         "initial_users": server_traffic_slider,
#         "initial_servers": 2,
#         "max_server_capacity": server_capacity_slider,
#         "server_failure_chance": server_failure_slider,
#     },
# )

# # Create ModularServer
# server = ModularServer(
#     LoadBalancerModel,
#     [grid],
#     "Load Balancer Model",
#     {"min_users": 10, "max_users": 30}
# )

# server.port = 8521
# server.launch()
